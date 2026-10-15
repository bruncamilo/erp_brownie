"""Compras de insumos: entrada de estoque com custo médio ponderado."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import RegraDeNegocio
from ..models import ATIVA, CANCELADA, Compra, CompraItem, Fornecedor, Insumo
from ..money import D, q2
from . import estoque


def registrar_compra(session: Session, *, data: date, itens: list[dict], fornecedor_id: int | None = None,
                     observacao: str = "") -> Compra:
    """itens: [{"insumo_id", "quantidade", "valor_total"}] (valor_total = o que foi pago pela quantidade)."""
    if not itens:
        raise RegraDeNegocio("Adicione ao menos um item à compra.")
    if fornecedor_id is not None:
        fornecedor = session.get(Fornecedor, fornecedor_id)
        if fornecedor is None or not fornecedor.ativo:
            raise RegraDeNegocio("Fornecedor inexistente ou inativo.")

    compra = Compra(data=data, fornecedor_id=fornecedor_id, observacao=observacao.strip(), status=ATIVA)
    session.add(compra)
    session.flush()

    total = D(0)
    for it in itens:
        insumo = session.get(Insumo, it["insumo_id"])
        quantidade, valor = D(it["quantidade"]), D(it["valor_total"])
        if insumo is None or not insumo.ativo:
            raise RegraDeNegocio("A compra tem um insumo inexistente ou inativo.")
        if quantidade <= 0:
            raise RegraDeNegocio(f"Informe a quantidade comprada de {insumo.nome}.")
        if valor < 0:
            raise RegraDeNegocio(f"O valor de {insumo.nome} não pode ser negativo.")
        compra.itens.append(CompraItem(insumo_id=insumo.id, quantidade=quantidade, valor_total=valor))
        estoque.entrada(session, insumo, quantidade, valor, "COMPRA", data, f"COMPRA:{compra.id}")
        total += valor
    compra.total = q2(total)
    session.flush()
    return compra


def cancelar_compra(session: Session, compra_id: int, data: date | None = None) -> Compra:
    """Estorna a entrada. Só é possível se os insumos ainda estiverem no estoque."""
    compra = session.get(Compra, compra_id)
    if compra is None:
        raise RegraDeNegocio("Compra não encontrada.")
    if compra.status == CANCELADA:
        raise RegraDeNegocio("Esta compra já está cancelada.")
    data = data or date.today()

    faltas = [
        f"{it.insumo.nome} (restam {estoque.num(it.insumo.estoque_atual)}, a compra trouxe {estoque.num(it.quantidade)})"
        for it in compra.itens if it.insumo.estoque_atual < it.quantidade
    ]
    if faltas:
        raise RegraDeNegocio(
            "Não dá para cancelar: parte dos insumos já foi usada em produção ou perda — " + "; ".join(faltas) + "."
        )
    for it in compra.itens:
        estoque.remover_valor(session, it.insumo, it.quantidade, it.valor_total, "ESTORNO_COMPRA", data,
                              f"COMPRA:{compra.id}", "Cancelamento de compra")
    compra.status = CANCELADA
    return compra


def listar(session: Session) -> list[Compra]:
    return list(session.scalars(select(Compra).order_by(Compra.data.desc(), Compra.id.desc())))
