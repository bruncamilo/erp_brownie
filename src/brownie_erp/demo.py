"""Dados de exemplo para demonstração e capturas de tela (python -m brownie_erp --demo)."""
from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .errors import RegraDeNegocio
from .models import FORMAS_PAGAMENTO, Insumo, Produto
from .services import cadastros, compras, despesas, producao, vendas

# nome, unidade, estoque mínimo, preço por unidade base (R$)
INSUMOS = [
    ("Chocolate meio amargo", "g", 1000, 0.038), ("Manteiga", "g", 500, 0.045), ("Açúcar refinado", "g", 1000, 0.005),
    ("Ovos", "un", 12, 0.85), ("Farinha de trigo", "g", 1000, 0.0055), ("Cacau em pó", "g", 200, 0.06),
    ("Nozes", "g", 200, 0.12), ("Doce de leite", "g", 300, 0.03), ("Caixa para 12 brownies", "un", 24, 0.9),
]
BASE = {"Chocolate meio amargo": 300, "Manteiga": 200, "Açúcar refinado": 300, "Ovos": 4, "Farinha de trigo": 150,
        "Cacau em pó": 40, "Caixa para 12 brownies": 12}
PRODUTOS = [  # nome, categoria, preço, extras da ficha
    ("Brownie tradicional", "Brownies", 9.0, {}),
    ("Brownie com nozes", "Brownies", 11.0, {"Nozes": 120}),
    ("Brownie de doce de leite", "Brownies", 10.0, {"Doce de leite": 200}),
]


def banco_vazio(session: Session) -> bool:
    return session.scalar(select(func.count()).select_from(Insumo)) == 0


def carregar_exemplo(session: Session, hoje: date | None = None) -> None:
    hoje = hoje or date.today()
    rnd = random.Random(7)
    ins = {n: cadastros.criar_insumo(session, n, u, m) for n, u, m, _ in INSUMOS}
    preco = {n: p for n, _, _, p in INSUMOS}
    forn = [cadastros.criar_fornecedor(session, n, t) for n, t in
            (("Atacadão do Doceiro", "(34) 3000-0001"), ("Mercado Central", "(34) 3000-0002"))]
    prods = {}
    for nome, cat, pv, extras in PRODUTOS:
        p = cadastros.criar_produto(session, nome, pv, rendimento=12, categoria=cat, estoque_minimo=12)
        ficha = {**BASE, **extras}
        cadastros.salvar_ficha(session, p.id, [{"insumo_id": ins[i].id, "quantidade": q} for i, q in ficha.items()])
        prods[nome] = p

    primeiro = date(hoje.year, hoje.month, 1)
    for k in range(5, -1, -1):  # 5 meses atrás até o mês atual
        mes = primeiro
        for _ in range(k):
            mes = (mes - timedelta(days=1)).replace(day=1)
        ajuste = 1 + rnd.uniform(-0.06, 0.08)
        d_compra = mes + timedelta(days=1)
        if d_compra <= hoje:
            itens = []
            for nome, _, _, _ in INSUMOS:
                lotes = 7
                qtd = sum(BASE.get(nome, 0) for _ in range(lotes)) + (360 if nome == "Nozes" else 600 if nome == "Doce de leite" else 0)
                if qtd:
                    itens.append({"insumo_id": ins[nome].id, "quantidade": qtd, "valor_total": round(qtd * preco[nome] * ajuste, 2)})
            compras.registrar_compra(session, data=d_compra, itens=itens, fornecedor_id=forn[k % 2].id)
        d_despesa = mes + timedelta(days=4)
        if d_despesa <= hoje:
            despesas.registrar_despesa(session, data=d_despesa, descricao="Botijão de gás", valor=round(110 * ajuste, 2), categoria="Gás e energia")
            despesas.registrar_despesa(session, data=d_despesa + timedelta(days=9), descricao="Entrega e combustível",
                                       valor=round(rnd.uniform(60, 120), 2), categoria="Transporte")
        nomes = list(prods)
        for dia in range(2, 29):
            d = mes + timedelta(days=dia)
            if d > hoje:
                break
            if dia in (3, 8, 13, 18, 23):
                p = prods[nomes[(dia // 7 + k) % 3]]
                try:
                    producao.registrar_producao(session, data=d, produto_id=p.id, lotes=rnd.choice([1, 2, 2]))
                except RegraDeNegocio:
                    pass
            if dia % 3 != 0:
                disponiveis = [p for p in prods.values() if p.estoque_atual >= 2]
                if disponiveis:
                    p = rnd.choice(disponiveis)
                    qtd = min(int(p.estoque_atual), rnd.randint(2, 7))
                    desc = rnd.choice([0, 0, 0, 2, 5])
                    try:
                        vendas.registrar_venda(
                            session, data=d, cliente=rnd.choice(["", "", "Marina", "Escritório da Ana", "Pedro", "Casamento Lúcia"]),
                            forma_pagamento=rnd.choice(FORMAS_PAGAMENTO), desconto=desc if desc < qtd * p.preco_venda else 0,
                            itens=[{"produto_id": p.id, "quantidade": qtd, "preco_unitario": p.preco_venda}])
                    except RegraDeNegocio:
                        pass
    session.flush()
