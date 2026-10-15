"""Relatórios gerenciais. O volume é pequeno, então agregamos em Python (mais legível que SQL)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ATIVA, Compra, Despesa, Insumo, Produto, Venda
from ..money import ZERO


@dataclass
class Resumo:
    """Resultado simplificado do período: receita - custo das vendas - despesas."""

    receita: Decimal
    cmv: Decimal                # custo dos produtos vendidos (custo registrado no dia da venda)
    lucro_bruto: Decimal
    despesas: Decimal
    resultado: Decimal
    num_vendas: int
    ticket_medio: Decimal
    compras_insumos: Decimal    # caixa gasto com insumos no período (informativo)

    @property
    def margem_bruta_pct(self) -> Decimal:
        return self.lucro_bruto / self.receita * 100 if self.receita else ZERO


def _vendas(session: Session, inicio: date, fim: date) -> list[Venda]:
    stmt = select(Venda).where(Venda.status == ATIVA, Venda.data >= inicio, Venda.data <= fim)
    return list(session.scalars(stmt))


def resumo_periodo(session: Session, inicio: date, fim: date) -> Resumo:
    vendas = _vendas(session, inicio, fim)
    receita = sum((v.total for v in vendas), ZERO)
    cmv = sum((i.quantidade * i.custo_unitario for v in vendas for i in v.itens), ZERO)
    despesas = sum((d.valor for d in session.scalars(
        select(Despesa).where(Despesa.data >= inicio, Despesa.data <= fim))), ZERO)
    compras = sum((c.total for c in session.scalars(
        select(Compra).where(Compra.status == ATIVA, Compra.data >= inicio, Compra.data <= fim))), ZERO)
    n = len(vendas)
    return Resumo(receita, cmv, receita - cmv, despesas, receita - cmv - despesas, n,
                  receita / n if n else ZERO, compras)


def top_produtos(session: Session, inicio: date, fim: date, limite: int = 10) -> list[dict]:
    """Produtos por receita. O desconto é rateado entre os itens da venda."""
    acc: dict[str, dict] = defaultdict(lambda: {"quantidade": ZERO, "receita": ZERO, "lucro": ZERO})
    for v in _vendas(session, inicio, fim):
        bruto = sum((i.quantidade * i.preco_unitario for i in v.itens), ZERO)
        for i in v.itens:
            linha = i.quantidade * i.preco_unitario
            liquido = linha - (v.desconto * linha / bruto if bruto else ZERO)
            a = acc[i.produto.nome]
            a["quantidade"] += i.quantidade
            a["receita"] += liquido
            a["lucro"] += liquido - i.quantidade * i.custo_unitario
    linhas = [{"produto": nome, **valores} for nome, valores in acc.items()]
    return sorted(linhas, key=lambda x: x["receita"], reverse=True)[:limite]


def vendas_por_forma_pagamento(session: Session, inicio: date, fim: date) -> list[tuple[str, Decimal]]:
    acc: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for v in _vendas(session, inicio, fim):
        acc[v.forma_pagamento] += v.total
    return sorted(acc.items(), key=lambda x: x[1], reverse=True)


def despesas_por_categoria(session: Session, inicio: date, fim: date) -> list[tuple[str, Decimal]]:
    acc: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for d in session.scalars(select(Despesa).where(Despesa.data >= inicio, Despesa.data <= fim)):
        acc[d.categoria] += d.valor
    return sorted(acc.items(), key=lambda x: x[1], reverse=True)


def estoque_baixo(session: Session) -> list[dict]:
    """Itens ativos com saldo igual ou abaixo do mínimo (mínimo 0 = sem alerta)."""
    itens: list[dict] = []
    for i in session.scalars(select(Insumo).where(Insumo.ativo.is_(True))):
        if i.estoque_minimo > 0 and i.estoque_atual <= i.estoque_minimo:
            itens.append({"tipo": "Insumo", "nome": i.nome, "unidade": i.unidade,
                          "atual": i.estoque_atual, "minimo": i.estoque_minimo})
    for p in session.scalars(select(Produto).where(Produto.ativo.is_(True))):
        if p.estoque_minimo > 0 and p.estoque_atual <= p.estoque_minimo:
            itens.append({"tipo": "Produto", "nome": p.nome, "unidade": "un",
                          "atual": p.estoque_atual, "minimo": p.estoque_minimo})
    return itens


def valor_em_estoque(session: Session) -> tuple[Decimal, Decimal]:
    """(insumos, produtos acabados) valorizados pelo custo médio."""
    ins = sum((i.estoque_atual * i.custo_medio for i in session.scalars(select(Insumo))), ZERO)
    prod = sum((p.estoque_atual * p.custo_medio for p in session.scalars(select(Produto))), ZERO)
    return ins, prod


def _somar_meses(ano: int, mes: int, delta: int) -> tuple[int, int]:
    indice = ano * 12 + (mes - 1) + delta
    return indice // 12, indice % 12 + 1


def serie_mensal(session: Session, meses: int = 6, hoje: date | None = None) -> list[dict]:
    """Receita e despesas (despesas + custo dos produtos vendidos) por mês, do mais antigo ao atual."""
    hoje = hoje or date.today()
    saida = []
    for k in range(meses - 1, -1, -1):
        ano, mes = _somar_meses(hoje.year, hoje.month, -k)
        ini = date(ano, mes, 1)
        prox_ano, prox_mes = _somar_meses(ano, mes, 1)
        fim = date.fromordinal(date(prox_ano, prox_mes, 1).toordinal() - 1)
        r = resumo_periodo(session, ini, fim)
        saida.append({"ano": ano, "mes": mes, "receita": r.receita, "custos": r.cmv + r.despesas,
                      "resultado": r.resultado})
    return saida
