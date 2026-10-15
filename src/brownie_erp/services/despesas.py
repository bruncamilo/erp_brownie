"""Despesas operacionais (gás, taxas, transporte...). Insumos NÃO entram aqui: vão por compras."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import RegraDeNegocio
from ..models import Despesa
from ..money import D


def registrar_despesa(session: Session, *, data: date, descricao: str, valor, categoria: str = "Outros") -> Despesa:
    if not descricao.strip():
        raise RegraDeNegocio("Descreva a despesa.")
    if D(valor) <= 0:
        raise RegraDeNegocio("O valor da despesa deve ser maior que zero.")
    d = Despesa(data=data, descricao=descricao.strip(), categoria=categoria.strip() or "Outros", valor=D(valor))
    session.add(d)
    session.flush()
    return d


def excluir_despesa(session: Session, despesa_id: int) -> None:
    d = session.get(Despesa, despesa_id)
    if d is None:
        raise RegraDeNegocio("Despesa não encontrada.")
    session.delete(d)


def listar(session: Session) -> list[Despesa]:
    return list(session.scalars(select(Despesa).order_by(Despesa.data.desc(), Despesa.id.desc())))
