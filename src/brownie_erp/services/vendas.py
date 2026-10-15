"""Vendas: baixa de produto acabado, desconto e custo registrado no dia da venda."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import RegraDeNegocio
from ..models import ATIVA, CANCELADA, FORMAS_PAGAMENTO, Produto, Venda, VendaItem
from ..money import ZERO, D, q2
from . import estoque


def registrar_venda(session: Session, *, data: date, itens: list[dict], cliente: str = "",
                    forma_pagamento: str = "PIX", desconto=0) -> Venda:
    """itens: [{"produto_id", "quantidade", "preco_unitario"}]."""
    if not itens:
        raise RegraDeNegocio("Adicione ao menos um item à venda.")
    if forma_pagamento not in FORMAS_PAGAMENTO:
        raise RegraDeNegocio("Forma de pagamento inválida.")
    desconto = D(desconto)
    if desconto < 0:
        raise RegraDeNegocio("O desconto não pode ser negativo.")

    # Valida tudo antes de mexer no estoque (mesmo produto pode aparecer em mais de uma linha)
    pedido: dict[int, object] = defaultdict(lambda: ZERO)
    subtotal = ZERO
    for it in itens:
        produto = session.get(Produto, it["produto_id"])
        qtd, preco = D(it["quantidade"]), D(it["preco_unitario"])
        if produto is None or not produto.ativo:
            raise RegraDeNegocio("A venda tem um produto inexistente ou inativo.")
        if qtd <= 0:
            raise RegraDeNegocio(f"Informe a quantidade de {produto.nome}.")
        if preco < 0:
            raise RegraDeNegocio(f"O preço de {produto.nome} não pode ser negativo.")
        pedido[produto.id] += qtd
        subtotal += qtd * preco
    for produto_id, qtd in pedido.items():
        produto = session.get(Produto, produto_id)
        if produto.estoque_atual < qtd:
            raise RegraDeNegocio(
                f"Estoque insuficiente de {produto.nome}: há {estoque.num(produto.estoque_atual)} un "
                f"e a venda pede {estoque.num(qtd)} un."
            )
    if desconto > subtotal:
        raise RegraDeNegocio("O desconto não pode ser maior que o total da venda.")

    venda = Venda(data=data, cliente=cliente.strip(), forma_pagamento=forma_pagamento, desconto=desconto,
                  total=q2(subtotal - desconto), status=ATIVA)
    session.add(venda)
    session.flush()
    for it in itens:
        produto = session.get(Produto, it["produto_id"])
        qtd = D(it["quantidade"])
        mov = estoque.saida(session, produto, qtd, "VENDA", data, f"VENDA:{venda.id}")
        venda.itens.append(VendaItem(produto_id=produto.id, quantidade=qtd, preco_unitario=D(it["preco_unitario"]),
                                     custo_unitario=mov.custo_unitario))
    session.flush()
    return venda


def cancelar_venda(session: Session, venda_id: int, data: date | None = None) -> Venda:
    venda = session.get(Venda, venda_id)
    if venda is None:
        raise RegraDeNegocio("Venda não encontrada.")
    if venda.status == CANCELADA:
        raise RegraDeNegocio("Esta venda já está cancelada.")
    data = data or date.today()
    for it in venda.itens:
        estoque.entrada(session, it.produto, it.quantidade, it.quantidade * it.custo_unitario, "ESTORNO_VENDA",
                        data, f"VENDA:{venda.id}", "Cancelamento de venda")
    venda.status = CANCELADA
    return venda


def custo_da_venda(venda: Venda):
    return sum((i.quantidade * i.custo_unitario for i in venda.itens), ZERO)


def listar(session: Session) -> list[Venda]:
    return list(session.scalars(select(Venda).order_by(Venda.data.desc(), Venda.id.desc())))
