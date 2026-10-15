from decimal import Decimal

import pytest

from brownie_erp.errors import RegraDeNegocio
from brownie_erp.models import CANCELADA, MovimentoEstoque
from brownie_erp.services import compras, estoque
from conftest import HOJE


def test_custo_medio_ponderado(session, cenario):
    ch = cenario["chocolate"]
    compras.registrar_compra(session, data=HOJE, itens=[{"insumo_id": ch.id, "quantidade": 1000, "valor_total": 40}])
    assert ch.estoque_atual == 1000 and ch.custo_medio == Decimal("0.04")
    # segunda compra mais cara: 1000 g por R$ 60 -> média de R$ 0,05/g
    compras.registrar_compra(session, data=HOJE, itens=[{"insumo_id": ch.id, "quantidade": 1000, "valor_total": 60}])
    assert ch.estoque_atual == 2000 and ch.custo_medio == Decimal("0.05")


def test_compra_gera_movimento_e_total(session, cenario):
    ch = cenario["chocolate"]
    c = compras.registrar_compra(session, data=HOJE, itens=[{"insumo_id": ch.id, "quantidade": 500, "valor_total": "22.50"}])
    assert c.total == Decimal("22.50")
    mov = session.query(MovimentoEstoque).one()
    assert mov.tipo == "COMPRA" and mov.quantidade == 500 and mov.documento == f"COMPRA:{c.id}"


def test_compra_validacoes(session, cenario):
    ch = cenario["chocolate"]
    with pytest.raises(RegraDeNegocio):
        compras.registrar_compra(session, data=HOJE, itens=[])
    with pytest.raises(RegraDeNegocio):
        compras.registrar_compra(session, data=HOJE, itens=[{"insumo_id": ch.id, "quantidade": 0, "valor_total": 5}])


def test_cancelar_compra_devolve_saldo_e_custo(session, cenario):
    ch = cenario["chocolate"]
    compras.registrar_compra(session, data=HOJE, itens=[{"insumo_id": ch.id, "quantidade": 1000, "valor_total": 40}])
    c2 = compras.registrar_compra(session, data=HOJE, itens=[{"insumo_id": ch.id, "quantidade": 1000, "valor_total": 60}])
    compras.cancelar_compra(session, c2.id)
    assert c2.status == CANCELADA
    assert ch.estoque_atual == 1000 and ch.custo_medio == Decimal("0.04")
    with pytest.raises(RegraDeNegocio):
        compras.cancelar_compra(session, c2.id)  # já cancelada


def test_nao_cancela_compra_se_insumo_ja_foi_usado(session, cenario):
    ch = cenario["chocolate"]
    c = compras.registrar_compra(session, data=HOJE, itens=[{"insumo_id": ch.id, "quantidade": 1000, "valor_total": 40}])
    estoque.registrar_perda(session, "INSUMO", ch.id, 300, HOJE)
    with pytest.raises(RegraDeNegocio, match="já foi usada"):
        compras.cancelar_compra(session, c.id)


def test_saldo_nunca_fica_negativo(session, cenario):
    ch = cenario["chocolate"]
    with pytest.raises(RegraDeNegocio, match="Estoque insuficiente"):
        estoque.registrar_perda(session, "INSUMO", ch.id, 1, HOJE)


def test_ajuste_de_inventario(session, cenario):
    ch = cenario["chocolate"]
    compras.registrar_compra(session, data=HOJE, itens=[{"insumo_id": ch.id, "quantidade": 1000, "valor_total": 40}])
    estoque.ajustar_inventario(session, "INSUMO", ch.id, 850, HOJE, "contei na prateleira")
    assert ch.estoque_atual == 850
    ultimo = session.query(MovimentoEstoque).order_by(MovimentoEstoque.id.desc()).first()
    assert ultimo.tipo == "AJUSTE" and ultimo.quantidade == -150
    assert estoque.ajustar_inventario(session, "INSUMO", ch.id, 850, HOJE) is None  # sem diferença
