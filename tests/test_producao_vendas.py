from decimal import Decimal

import pytest

from brownie_erp.errors import RegraDeNegocio
from brownie_erp.services import compras, producao, relatorios, vendas
from conftest import HOJE


@pytest.fixture()
def abastecido(session, cenario):
    ch, ov = cenario["chocolate"], cenario["ovos"]
    compras.registrar_compra(session, data=HOJE, itens=[
        {"insumo_id": ch.id, "quantidade": 2000, "valor_total": 80},    # R$ 0,04/g
        {"insumo_id": ov.id, "quantidade": 30, "valor_total": 18},      # R$ 0,60/un
    ])
    session.commit()
    return cenario


def test_producao_consome_ficha_e_gera_produto(session, abastecido):
    b = abastecido["brownie"]
    p = producao.registrar_producao(session, data=HOJE, produto_id=b.id, lotes=2)
    # 2 lotes: 800 g de chocolate (R$ 32) + 8 ovos (R$ 4,80) = R$ 36,80
    assert p.quantidade == 24 and p.custo_total == Decimal("36.80")
    assert abastecido["chocolate"].estoque_atual == 1200
    assert abastecido["ovos"].estoque_atual == 22
    assert b.estoque_atual == 24
    assert abs(b.custo_medio - Decimal("1.533333")) < Decimal("0.000001")   # 36,80 / 24


def test_producao_bloqueia_se_faltar_insumo_e_nao_altera_nada(session, abastecido):
    b = abastecido["brownie"]
    with pytest.raises(RegraDeNegocio, match="Ovos: faltam"):
        producao.registrar_producao(session, data=HOJE, produto_id=b.id, lotes=10)  # precisa de 40 ovos
    session.rollback()
    assert abastecido["chocolate"].estoque_atual == 2000


def test_producao_exige_ficha(session, cenario):
    from brownie_erp.services import cadastros
    sem_ficha = cadastros.criar_produto(session, "Cookie", 6)
    with pytest.raises(RegraDeNegocio, match="ficha técnica"):
        producao.registrar_producao(session, data=HOJE, produto_id=sem_ficha.id, lotes=1)


def test_cancelar_producao_devolve_insumos(session, abastecido):
    b = abastecido["brownie"]
    p = producao.registrar_producao(session, data=HOJE, produto_id=b.id, lotes=1)
    producao.cancelar_producao(session, p.id)
    assert abastecido["chocolate"].estoque_atual == 2000
    assert abastecido["ovos"].estoque_atual == 30
    assert b.estoque_atual == 0


def test_nao_cancela_producao_se_ja_vendeu(session, abastecido):
    b = abastecido["brownie"]
    p = producao.registrar_producao(session, data=HOJE, produto_id=b.id, lotes=1)
    vendas.registrar_venda(session, data=HOJE, itens=[{"produto_id": b.id, "quantidade": 5, "preco_unitario": 9}])
    with pytest.raises(RegraDeNegocio, match="já foi vendida"):
        producao.cancelar_producao(session, p.id)


def test_venda_baixa_estoque_guarda_custo_e_aplica_desconto(session, abastecido):
    b = abastecido["brownie"]
    producao.registrar_producao(session, data=HOJE, produto_id=b.id, lotes=1)   # 12 un, custo 18,40
    v = vendas.registrar_venda(session, data=HOJE, forma_pagamento="PIX", desconto="2",
                               itens=[{"produto_id": b.id, "quantidade": 4, "preco_unitario": 9}])
    assert v.total == Decimal("34.00")                      # 36 - 2
    assert b.estoque_atual == 8
    assert v.itens[0].custo_unitario == b.custo_medio       # custo congelado no dia


def test_venda_sem_estoque_e_bloqueada(session, abastecido):
    b = abastecido["brownie"]
    producao.registrar_producao(session, data=HOJE, produto_id=b.id, lotes=1)
    with pytest.raises(RegraDeNegocio, match="Estoque insuficiente"):
        vendas.registrar_venda(session, data=HOJE, itens=[
            {"produto_id": b.id, "quantidade": 8, "preco_unitario": 9},
            {"produto_id": b.id, "quantidade": 8, "preco_unitario": 9},   # soma 16 > 12
        ])


def test_desconto_nao_pode_passar_do_total(session, abastecido):
    b = abastecido["brownie"]
    producao.registrar_producao(session, data=HOJE, produto_id=b.id, lotes=1)
    with pytest.raises(RegraDeNegocio, match="desconto"):
        vendas.registrar_venda(session, data=HOJE, desconto=100,
                               itens=[{"produto_id": b.id, "quantidade": 1, "preco_unitario": 9}])


def test_cancelar_venda_devolve_ao_estoque(session, abastecido):
    b = abastecido["brownie"]
    producao.registrar_producao(session, data=HOJE, produto_id=b.id, lotes=1)
    v = vendas.registrar_venda(session, data=HOJE, itens=[{"produto_id": b.id, "quantidade": 3, "preco_unitario": 9}])
    vendas.cancelar_venda(session, v.id)
    assert b.estoque_atual == 12 and v.status == "CANCELADA"


def test_resumo_do_periodo(session, abastecido):
    from brownie_erp.services import despesas
    b = abastecido["brownie"]
    producao.registrar_producao(session, data=HOJE, produto_id=b.id, lotes=1)      # custo/un = 18,40 / 12
    vendas.registrar_venda(session, data=HOJE, itens=[{"produto_id": b.id, "quantidade": 6, "preco_unitario": 9}])
    cancelada = vendas.registrar_venda(session, data=HOJE, itens=[{"produto_id": b.id, "quantidade": 2, "preco_unitario": 9}])
    vendas.cancelar_venda(session, cancelada.id)                                    # não conta no resultado
    despesas.registrar_despesa(session, data=HOJE, descricao="Gás", valor=10, categoria="Gás e energia")
    r = relatorios.resumo_periodo(session, HOJE, HOJE)
    assert r.receita == 54 and r.num_vendas == 1
    assert abs(r.cmv - Decimal("9.20")) < Decimal("0.0001")
    assert abs(r.resultado - (54 - Decimal("9.20") - 10)) < Decimal("0.0001")
    top = relatorios.top_produtos(session, HOJE, HOJE)
    assert top[0]["produto"] == "Brownie tradicional" and top[0]["quantidade"] == 6
