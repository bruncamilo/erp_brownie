"""Dinheiro e quantidades com Decimal.

No banco, valores são guardados como inteiros (valor x 1.000.000). Isso evita erros de
ponto flutuante e mantém SUM/ORDER BY corretos em SQL.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import BigInteger
from sqlalchemy.types import TypeDecorator

SCALE = 1_000_000
ZERO = Decimal(0)
_CENT = Decimal("0.01")
_MICRO = Decimal("0.000001")


def D(value) -> Decimal:
    """Converte qualquer valor (str, int, float, Decimal, None) em Decimal."""
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return ZERO
    return Decimal(str(value))


def q2(value) -> Decimal:
    """Arredonda para centavos."""
    return D(value).quantize(_CENT, rounding=ROUND_HALF_UP)


def q6(value) -> Decimal:
    """Arredonda para a precisão máxima armazenada (6 casas)."""
    return D(value).quantize(_MICRO, rounding=ROUND_HALF_UP)


class Dec(TypeDecorator):
    """Decimal armazenado como inteiro escalado."""

    impl = BigInteger
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return int((D(value) * SCALE).quantize(Decimal(1), rounding=ROUND_HALF_UP))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Decimal(value) / SCALE


def brl(value) -> str:
    """Formata como moeda brasileira: R$ 1.234,56."""
    v = q2(value)
    texto = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {texto}" if v < 0 else f"R$ {texto}"


def num(value, casas: int = 3) -> str:
    """Formata quantidade sem zeros à direita: 1.250,5."""
    v = D(value).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    texto = f"{v:,.{casas}f}".rstrip("0").rstrip(".")
    return texto.replace(",", "X").replace(".", ",").replace("X", ".") if texto else "0"


def pct(value) -> str:
    return f"{D(value).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%".replace(".", ",")
