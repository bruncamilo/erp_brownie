"""Movimentação de estoque: único ponto que altera saldo de insumos e produtos.

Regras:
- Saldo nunca fica negativo.
- Toda alteração gera um movimento (kardex) com documento de origem.
- Custo médio ponderado é recalculado a cada entrada com custo.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import RegraDeNegocio
from ..models import Insumo, MovimentoEstoque, Produto
from ..money import ZERO, D, num, q6

INSUMO = "INSUMO"
PRODUTO = "PRODUTO"


def _rotulo(item) -> str:
    unidade = getattr(item, "unidade", "un")
    return f"{item.nome} ({num(item.estoque_atual)} {unidade} em estoque)"


def _movimentar(session: Session, item, quantidade: Decimal, tipo: str, data: date,
                custo_unitario: Decimal, documento: str, observacao: str) -> MovimentoEstoque:
    quantidade = D(quantidade)
    novo_saldo = item.estoque_atual + quantidade
    if novo_saldo < 0:
        unidade = getattr(item, "unidade", "un")
        raise RegraDeNegocio(
            f"Estoque insuficiente de {item.nome}: há {num(item.estoque_atual)} {unidade} "
            f"e a operação precisa de {num(-quantidade)} {unidade}."
        )
    item.estoque_atual = novo_saldo
    mov = MovimentoEstoque(
        data=data, tipo=tipo, quantidade=quantidade, custo_unitario=q6(custo_unitario),
        documento=documento, observacao=observacao,
        insumo_id=item.id if isinstance(item, Insumo) else None,
        produto_id=item.id if isinstance(item, Produto) else None,
    )
    session.add(mov)
    return mov


def _custo_medio_apos_entrada(item, quantidade: Decimal, valor_total: Decimal) -> Decimal:
    novo_estoque = item.estoque_atual + quantidade
    if novo_estoque <= 0:
        return item.custo_medio
    return q6((item.estoque_atual * item.custo_medio + valor_total) / novo_estoque)


def entrada(session: Session, item, quantidade, valor_total, tipo: str, data: date,
            documento: str = "", observacao: str = "") -> MovimentoEstoque:
    """Entrada com custo: atualiza o custo médio ponderado e o saldo."""
    quantidade, valor_total = D(quantidade), D(valor_total)
    if quantidade <= 0:
        raise RegraDeNegocio("A quantidade deve ser maior que zero.")
    novo_custo = _custo_medio_apos_entrada(item, quantidade, valor_total)
    custo_unit = q6(valor_total / quantidade)
    mov = _movimentar(session, item, quantidade, tipo, data, custo_unit, documento, observacao)
    item.custo_medio = novo_custo
    return mov


def saida(session: Session, item, quantidade, tipo: str, data: date,
          documento: str = "", observacao: str = "") -> MovimentoEstoque:
    """Saída ao custo médio atual (o custo médio não muda numa saída)."""
    quantidade = D(quantidade)
    if quantidade <= 0:
        raise RegraDeNegocio("A quantidade deve ser maior que zero.")
    return _movimentar(session, item, -quantidade, tipo, data, item.custo_medio, documento, observacao)


def remover_valor(session: Session, item, quantidade, valor_total, tipo: str, data: date,
                  documento: str = "", observacao: str = "") -> MovimentoEstoque:
    """Estorno de uma entrada: tira quantidade e o valor correspondente do custo médio."""
    quantidade, valor_total = D(quantidade), D(valor_total)
    restante = item.estoque_atual - quantidade
    mov = _movimentar(session, item, -quantidade, tipo, data, item.custo_medio, documento, observacao)
    if restante > 0:
        valor_restante = max(item.custo_medio * (restante + quantidade) - valor_total, ZERO)
        item.custo_medio = q6(valor_restante / restante)
    return mov


def _carregar(session: Session, item_tipo: str, item_id: int):
    classe = Insumo if item_tipo == INSUMO else Produto
    item = session.get(classe, item_id)
    if item is None:
        raise RegraDeNegocio("Item não encontrado.")
    return item


def ajustar_inventario(session: Session, item_tipo: str, item_id: int, contagem, data: date,
                       observacao: str = "") -> MovimentoEstoque | None:
    """Ajuste por contagem física: define o saldo real e registra a diferença."""
    item = _carregar(session, item_tipo, item_id)
    contagem = D(contagem)
    if contagem < 0:
        raise RegraDeNegocio("A contagem não pode ser negativa.")
    diferenca = contagem - item.estoque_atual
    if diferenca == 0:
        return None
    return _movimentar(session, item, diferenca, "AJUSTE", data, item.custo_medio, "", observacao or "Contagem de estoque")


def registrar_perda(session: Session, item_tipo: str, item_id: int, quantidade, data: date,
                    observacao: str = "") -> MovimentoEstoque:
    """Perda/descarte (estragou, caiu, venceu). Sai do estoque ao custo médio."""
    item = _carregar(session, item_tipo, item_id)
    return saida(session, item, quantidade, "PERDA", data, "", observacao or "Perda")


def listar_movimentos(session: Session, limite: int = 500) -> list[MovimentoEstoque]:
    stmt = select(MovimentoEstoque).order_by(MovimentoEstoque.id.desc()).limit(limite)
    return list(session.scalars(stmt))
