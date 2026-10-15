"""Produção: transforma insumos em produto acabado seguindo a ficha técnica."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import RegraDeNegocio
from ..models import ATIVA, CANCELADA, MovimentoEstoque, Produto, Producao
from ..money import ZERO, D, q2
from . import estoque


@dataclass
class Necessidade:
    insumo_id: int
    insumo: str
    unidade: str
    necessario: Decimal
    disponivel: Decimal
    custo: Decimal

    @property
    def falta(self) -> Decimal:
        return max(self.necessario - self.disponivel, ZERO)


def necessidades(produto: Produto, lotes) -> list[Necessidade]:
    """O que seria consumido para produzir `lotes` (sem alterar nada)."""
    lotes = D(lotes)
    return [
        Necessidade(f.insumo_id, f.insumo.nome, f.insumo.unidade, f.quantidade * lotes,
                    f.insumo.estoque_atual, f.quantidade * lotes * f.insumo.custo_medio)
        for f in produto.ficha
    ]


def custo_lote(produto: Produto) -> Decimal:
    """Custo de um lote com os custos médios atuais dos insumos."""
    return sum((n.custo for n in necessidades(produto, 1)), ZERO)


def custo_unitario_estimado(produto: Produto) -> Decimal:
    return custo_lote(produto) / produto.rendimento if produto.rendimento else ZERO


def registrar_producao(session: Session, *, data: date, produto_id: int, lotes, observacao: str = "") -> Producao:
    produto = session.get(Produto, produto_id)
    lotes = D(lotes)
    if produto is None or not produto.ativo:
        raise RegraDeNegocio("Produto inexistente ou inativo.")
    if lotes <= 0:
        raise RegraDeNegocio("Informe quantos lotes foram produzidos.")
    if not produto.ficha:
        raise RegraDeNegocio(f"{produto.nome} não tem ficha técnica. Cadastre a ficha antes de produzir.")

    needs = necessidades(produto, lotes)
    faltas = [f"{n.insumo}: faltam {estoque.num(n.falta)} {n.unidade}" for n in needs if n.falta > 0]
    if faltas:
        raise RegraDeNegocio("Insumos insuficientes — " + "; ".join(faltas) + ".")

    quantidade = produto.rendimento * lotes
    producao = Producao(data=data, produto_id=produto.id, lotes=lotes, quantidade=quantidade,
                        observacao=observacao.strip(), status=ATIVA)
    session.add(producao)
    session.flush()
    doc = f"PRODUCAO:{producao.id}"

    custo_total = ZERO
    for f in produto.ficha:
        qtd = f.quantidade * lotes
        mov = estoque.saida(session, f.insumo, qtd, "PRODUCAO_CONSUMO", data, doc)
        custo_total += qtd * mov.custo_unitario
    producao.custo_total = q2(custo_total)
    estoque.entrada(session, produto, quantidade, custo_total, "PRODUCAO_ENTRADA", data, doc)
    session.flush()
    return producao


def cancelar_producao(session: Session, producao_id: int, data: date | None = None) -> Producao:
    """Devolve os insumos ao estoque (pelos movimentos originais) e retira o produto acabado."""
    producao = session.get(Producao, producao_id)
    if producao is None:
        raise RegraDeNegocio("Produção não encontrada.")
    if producao.status == CANCELADA:
        raise RegraDeNegocio("Esta produção já está cancelada.")
    data = data or date.today()
    produto = producao.produto
    if produto.estoque_atual < producao.quantidade:
        raise RegraDeNegocio(
            f"Não dá para cancelar: restam {estoque.num(produto.estoque_atual)} un de {produto.nome} "
            f"e esta produção gerou {estoque.num(producao.quantidade)} un (parte já foi vendida)."
        )
    doc = f"PRODUCAO:{producao.id}"
    consumos = session.scalars(
        select(MovimentoEstoque).where(MovimentoEstoque.documento == doc, MovimentoEstoque.tipo == "PRODUCAO_CONSUMO")
    ).all()
    for mov in consumos:
        qtd = -mov.quantidade
        estoque.entrada(session, mov.insumo, qtd, qtd * mov.custo_unitario, "ESTORNO_PRODUCAO", data, doc,
                        "Cancelamento de produção")
    estoque.remover_valor(session, produto, producao.quantidade, producao.custo_total, "ESTORNO_PRODUCAO", data, doc,
                          "Cancelamento de produção")
    producao.status = CANCELADA
    return producao


def listar(session: Session) -> list[Producao]:
    return list(session.scalars(select(Producao).order_by(Producao.data.desc(), Producao.id.desc())))
