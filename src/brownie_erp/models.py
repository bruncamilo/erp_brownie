"""Modelo de dados.

Convenções:
- Quantidades e valores usam o tipo `Dec` (Decimal exato).
- Nada de importância é apagado: cadastros são inativados e documentos são cancelados
  (com estorno de estoque). Toda alteração de estoque gera uma linha em `movimento_estoque`.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .money import ZERO, Dec

# Constantes de domínio
UNIDADES = ("g", "kg", "ml", "l", "un")
FORMAS_PAGAMENTO = ("PIX", "Dinheiro", "Débito", "Crédito")
CATEGORIAS_DESPESA = ("Embalagem", "Gás e energia", "Transporte", "Marketing", "Taxas", "Equipamentos", "Outros")
ATIVA = "ATIVA"
CANCELADA = "CANCELADA"


class Base(DeclarativeBase):
    pass


class Insumo(Base):
    __tablename__ = "insumo"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    unidade: Mapped[str] = mapped_column(String(10))
    estoque_atual: Mapped[Decimal] = mapped_column(Dec, default=ZERO)
    estoque_minimo: Mapped[Decimal] = mapped_column(Dec, default=ZERO)
    custo_medio: Mapped[Decimal] = mapped_column(Dec, default=ZERO)  # R$ por unidade
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Fornecedor(Base):
    __tablename__ = "fornecedor"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    telefone: Mapped[str] = mapped_column(String(30), default="")
    observacao: Mapped[str] = mapped_column(String(255), default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Produto(Base):
    __tablename__ = "produto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    categoria: Mapped[str] = mapped_column(String(60), default="")
    preco_venda: Mapped[Decimal] = mapped_column(Dec, default=ZERO)
    rendimento: Mapped[Decimal] = mapped_column(Dec, default=Decimal(1))  # unidades por lote
    estoque_atual: Mapped[Decimal] = mapped_column(Dec, default=ZERO)
    estoque_minimo: Mapped[Decimal] = mapped_column(Dec, default=ZERO)
    custo_medio: Mapped[Decimal] = mapped_column(Dec, default=ZERO)  # custo do produto acabado
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    ficha: Mapped[list[FichaItem]] = relationship(
        back_populates="produto", cascade="all, delete-orphan", order_by="FichaItem.id"
    )


class FichaItem(Base):
    """Linha da ficha técnica: quanto de cada insumo vai em UM lote do produto."""

    __tablename__ = "ficha_item"
    __table_args__ = (UniqueConstraint("produto_id", "insumo_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"))
    insumo_id: Mapped[int] = mapped_column(ForeignKey("insumo.id"))
    quantidade: Mapped[Decimal] = mapped_column(Dec)

    produto: Mapped[Produto] = relationship(back_populates="ficha")
    insumo: Mapped[Insumo] = relationship()


class Compra(Base):
    __tablename__ = "compra"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date)
    fornecedor_id: Mapped[int | None] = mapped_column(ForeignKey("fornecedor.id"), nullable=True)
    observacao: Mapped[str] = mapped_column(String(255), default="")
    total: Mapped[Decimal] = mapped_column(Dec, default=ZERO)
    status: Mapped[str] = mapped_column(String(12), default=ATIVA)

    fornecedor: Mapped[Fornecedor | None] = relationship()
    itens: Mapped[list[CompraItem]] = relationship(back_populates="compra", cascade="all, delete-orphan")


class CompraItem(Base):
    __tablename__ = "compra_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    compra_id: Mapped[int] = mapped_column(ForeignKey("compra.id"))
    insumo_id: Mapped[int] = mapped_column(ForeignKey("insumo.id"))
    quantidade: Mapped[Decimal] = mapped_column(Dec)
    valor_total: Mapped[Decimal] = mapped_column(Dec)

    compra: Mapped[Compra] = relationship(back_populates="itens")
    insumo: Mapped[Insumo] = relationship()


class Producao(Base):
    __tablename__ = "producao"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"))
    lotes: Mapped[Decimal] = mapped_column(Dec)
    quantidade: Mapped[Decimal] = mapped_column(Dec)  # unidades produzidas
    custo_total: Mapped[Decimal] = mapped_column(Dec, default=ZERO)
    observacao: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(12), default=ATIVA)

    produto: Mapped[Produto] = relationship()


class Venda(Base):
    __tablename__ = "venda"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date)
    cliente: Mapped[str] = mapped_column(String(120), default="")
    forma_pagamento: Mapped[str] = mapped_column(String(20), default="PIX")
    desconto: Mapped[Decimal] = mapped_column(Dec, default=ZERO)
    total: Mapped[Decimal] = mapped_column(Dec, default=ZERO)  # já com desconto
    status: Mapped[str] = mapped_column(String(12), default=ATIVA)

    itens: Mapped[list[VendaItem]] = relationship(back_populates="venda", cascade="all, delete-orphan")


class VendaItem(Base):
    __tablename__ = "venda_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    venda_id: Mapped[int] = mapped_column(ForeignKey("venda.id"))
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"))
    quantidade: Mapped[Decimal] = mapped_column(Dec)
    preco_unitario: Mapped[Decimal] = mapped_column(Dec)
    custo_unitario: Mapped[Decimal] = mapped_column(Dec, default=ZERO)  # custo no dia da venda

    venda: Mapped[Venda] = relationship(back_populates="itens")
    produto: Mapped[Produto] = relationship()


class Despesa(Base):
    __tablename__ = "despesa"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date)
    descricao: Mapped[str] = mapped_column(String(160))
    categoria: Mapped[str] = mapped_column(String(60), default="Outros")
    valor: Mapped[Decimal] = mapped_column(Dec)


class MovimentoEstoque(Base):
    """Livro-razão de estoque (kardex). Quantidade com sinal: entrada > 0, saída < 0."""

    __tablename__ = "movimento_estoque"

    id: Mapped[int] = mapped_column(primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    data: Mapped[date] = mapped_column(Date)
    tipo: Mapped[str] = mapped_column(String(24))
    insumo_id: Mapped[int | None] = mapped_column(ForeignKey("insumo.id"), nullable=True)
    produto_id: Mapped[int | None] = mapped_column(ForeignKey("produto.id"), nullable=True)
    quantidade: Mapped[Decimal] = mapped_column(Dec)
    custo_unitario: Mapped[Decimal] = mapped_column(Dec, default=ZERO)
    documento: Mapped[str] = mapped_column(String(30), default="")  # ex.: "COMPRA:12"
    observacao: Mapped[str] = mapped_column(Text, default="")

    insumo: Mapped[Insumo | None] = relationship()
    produto: Mapped[Produto | None] = relationship()
