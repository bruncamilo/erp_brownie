import pytest

from brownie_erp.errors import RegraDeNegocio
from brownie_erp.services import cadastros, compras, precificacao, producao
from conftest import HOJE


def test_nome_duplicado_ignora_maiusculas(session, cenario):
    with pytest.raises(RegraDeNegocio, match="Já existe"):
        cadastros.criar_insumo(session, "  ovos ", "un")


def test_unidade_nao_muda_apos_movimentacao(session, cenario):
    ov = cenario["ovos"]
    compras.registrar_compra(session, data=HOJE, itens=[{"insumo_id": ov.id, "quantidade": 12, "valor_total": 9}])
    with pytest.raises(RegraDeNegocio, match="unidade"):
        cadastros.atualizar_insumo(session, ov.id, "Ovos", "kg")


def test_insumo_em_ficha_nao_pode_ser_inativado(session, cenario):
    with pytest.raises(RegraDeNegocio, match="Brownie tradicional"):
        cadastros.definir_insumo_ativo(session, cenario["ovos"].id, False)


def test_produto_com_estoque_nao_pode_ser_inativado(session, cenario):
    ch, ov, b = cenario["chocolate"], cenario["ovos"], cenario["brownie"]
    compras.registrar_compra(session, data=HOJE, itens=[
        {"insumo_id": ch.id, "quantidade": 400, "valor_total": 16}, {"insumo_id": ov.id, "quantidade": 4, "valor_total": 2.4}])
    producao.registrar_producao(session, data=HOJE, produto_id=b.id, lotes=1)
    with pytest.raises(RegraDeNegocio, match="com estoque"):
        cadastros.definir_produto_ativo(session, b.id, False)


def test_ficha_nao_aceita_insumo_repetido_nem_quantidade_zero(session, cenario):
    ch, b = cenario["chocolate"], cenario["brownie"]
    with pytest.raises(RegraDeNegocio, match="duas vezes"):
        cadastros.salvar_ficha(session, b.id, [{"insumo_id": ch.id, "quantidade": 1}, {"insumo_id": ch.id, "quantidade": 2}])
    with pytest.raises(RegraDeNegocio):
        cadastros.salvar_ficha(session, b.id, [{"insumo_id": ch.id, "quantidade": 0}])


def test_custo_estimado_e_preco_sugerido(session, cenario):
    ch, ov, b = cenario["chocolate"], cenario["ovos"], cenario["brownie"]
    compras.registrar_compra(session, data=HOJE, itens=[
        {"insumo_id": ch.id, "quantidade": 1000, "valor_total": 40}, {"insumo_id": ov.id, "quantidade": 10, "valor_total": 6}])
    # 400 g * 0,04 + 4 ovos * 0,60 = 18,40 por lote de 12
    assert float(producao.custo_lote(b)) == pytest.approx(18.4)
    assert float(producao.custo_unitario_estimado(b)) == pytest.approx(18.4 / 12)
    assert float(precificacao.preco_sugerido(10, 60)) == pytest.approx(25)
    assert float(precificacao.margem_percentual(9, 3)) == pytest.approx(66.666, rel=1e-3)
