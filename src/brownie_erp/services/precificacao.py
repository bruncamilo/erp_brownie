"""Margem e preço sugerido."""
from __future__ import annotations

from decimal import Decimal

from ..money import ZERO, D


def margem_percentual(preco, custo) -> Decimal | None:
    """Margem sobre o preço de venda: (preço - custo) / preço."""
    preco, custo = D(preco), D(custo)
    if preco <= 0:
        return None
    return (preco - custo) / preco * 100


def preco_sugerido(custo, margem_desejada_pct) -> Decimal:
    """Preço para atingir a margem desejada sobre o preço de venda."""
    margem = D(margem_desejada_pct) / 100
    if margem >= 1:
        return ZERO
    return D(custo) / (1 - margem)
