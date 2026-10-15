"""Páginas de lançamentos: compras, produção, vendas, despesas e movimentação de estoque."""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from ...db import session_scope
from ...models import CANCELADA, Compra
from ...money import brl, num
from ...services import compras, despesas, estoque, producao, vendas
from .. import dialogs
from ..widgets import Page, confirmar

NOMES_TIPO = {
    "COMPRA": "Compra", "ESTORNO_COMPRA": "Cancelamento de compra",
    "PRODUCAO_CONSUMO": "Uso na produção", "PRODUCAO_ENTRADA": "Produção", "ESTORNO_PRODUCAO": "Cancelamento de produção",
    "VENDA": "Venda", "ESTORNO_VENDA": "Cancelamento de venda", "AJUSTE": "Contagem", "PERDA": "Perda",
}


def _situacao(status: str) -> str:
    return "Cancelada" if status == CANCELADA else "Ativa"


def _tom(status: str) -> str | None:
    return "suave" if status == CANCELADA else None


class ComprasPage(Page):
    titulo = "Compras"
    subtitulo = "Cada compra aumenta o estoque e atualiza o custo médio dos insumos."
    colunas = ["Nº", "Data", "Fornecedor", "Itens", "Total", "Situação"]
    numericas = (4,)
    coluna_esticada = 3
    mensagem_vazia = "Nenhuma compra registrada ainda."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.acao("Nova compra", self.nova, primario=True)
        self.acao("Ver itens", self.ver)
        self.acao("Cancelar compra", self.cancelar, perigo=True)

    def linhas(self, s):
        return [(c.id, [str(c.id), c.data.strftime("%d/%m/%Y"), c.fornecedor.nome if c.fornecedor else "–",
                        ", ".join(f"{i.insumo.nome}" for i in c.itens), brl(c.total), _situacao(c.status)], _tom(c.status))
                for c in compras.listar(s)]

    def nova(self):
        if dialogs.CompraDialog(self).exec():
            self.refresh()

    def ver(self):
        rid = self.selecionado()
        if not rid:
            return
        with session_scope() as s:
            c = s.get(Compra, rid)
            texto = "\n".join(f"• {num(i.quantidade)} {i.insumo.unidade} de {i.insumo.nome} — {brl(i.valor_total)}"
                              for i in c.itens)
            titulo = f"Compra nº {c.id} — {c.data:%d/%m/%Y}"
        QMessageBox.information(self, titulo, texto)

    ao_duplo_clique = ver

    def cancelar(self):
        rid = self.selecionado()
        if rid and confirmar(self, "Cancelar compra", "Os insumos desta compra saem do estoque e o custo médio é "
                             "recalculado. Continuar?", "Cancelar compra"):
            self.executar(lambda s: compras.cancelar_compra(s, rid))


class ProducaoPage(Page):
    titulo = "Produção"
    subtitulo = "Produzir consome os insumos da ficha técnica e coloca o produto pronto no estoque."
    colunas = ["Nº", "Data", "Produto", "Lotes", "Unidades", "Custo total", "Custo por un.", "Situação"]
    numericas = (3, 4, 5, 6)
    coluna_esticada = 2
    mensagem_vazia = "Nenhuma produção registrada ainda."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.acao("Nova produção", self.nova, primario=True)
        self.acao("Cancelar produção", self.cancelar, perigo=True)

    def linhas(self, s):
        return [(p.id, [str(p.id), p.data.strftime("%d/%m/%Y"), p.produto.nome, num(p.lotes), num(p.quantidade),
                        brl(p.custo_total), brl(p.custo_total / p.quantidade if p.quantidade else 0), _situacao(p.status)],
                _tom(p.status)) for p in producao.listar(s)]

    def nova(self):
        if dialogs.ProducaoDialog(self).exec():
            self.refresh()

    def cancelar(self):
        rid = self.selecionado()
        if rid and confirmar(self, "Cancelar produção", "Os insumos voltam ao estoque e os produtos desta produção "
                             "saem. Só é possível se eles ainda não foram vendidos. Continuar?", "Cancelar produção"):
            self.executar(lambda s: producao.cancelar_producao(s, rid))


class VendasPage(Page):
    titulo = "Vendas"
    subtitulo = "Cada venda baixa o estoque e guarda o custo do dia, para o lucro não mudar depois."
    colunas = ["Nº", "Data", "Cliente", "Pagamento", "Itens", "Desconto", "Total", "Lucro", "Situação"]
    numericas = (5, 6, 7)
    coluna_esticada = 4
    mensagem_vazia = "Nenhuma venda registrada ainda."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.acao("Nova venda", self.nova, primario=True)
        self.acao("Cancelar venda", self.cancelar, perigo=True)

    def linhas(self, s):
        saida = []
        for v in vendas.listar(s):
            itens = ", ".join(f"{num(i.quantidade)}× {i.produto.nome}" for i in v.itens)
            saida.append((v.id, [str(v.id), v.data.strftime("%d/%m/%Y"), v.cliente or "–", v.forma_pagamento, itens,
                                 brl(v.desconto) if v.desconto else "–", brl(v.total),
                                 brl(v.total - vendas.custo_da_venda(v)), _situacao(v.status)], _tom(v.status)))
        return saida

    def nova(self):
        if dialogs.VendaDialog(self).exec():
            self.refresh()

    def cancelar(self):
        rid = self.selecionado()
        if rid and confirmar(self, "Cancelar venda", "Os produtos voltam ao estoque e a venda deixa de contar no "
                             "resultado. Continuar?", "Cancelar venda"):
            self.executar(lambda s: vendas.cancelar_venda(s, rid))


class DespesasPage(Page):
    titulo = "Despesas"
    subtitulo = "Gás, taxas, transporte e outros gastos que não são ingredientes."
    colunas = ["Data", "Descrição", "Categoria", "Valor"]
    numericas = (3,)
    coluna_esticada = 1
    mensagem_vazia = "Nenhuma despesa registrada ainda."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.acao("Nova despesa", self.nova, primario=True)
        self.acao("Excluir", self.excluir, perigo=True)

    def linhas(self, s):
        return [(d.id, [d.data.strftime("%d/%m/%Y"), d.descricao, d.categoria, brl(d.valor)], None)
                for d in despesas.listar(s)]

    def nova(self):
        if dialogs.DespesaDialog(self).exec():
            self.refresh()

    def excluir(self):
        rid = self.selecionado()
        if rid and confirmar(self, "Excluir despesa", "Excluir esta despesa? Ela deixa de contar no resultado.", "Excluir"):
            self.executar(lambda s: despesas.excluir_despesa(s, rid))


class MovimentosPage(Page):
    titulo = "Movimentação de estoque"
    subtitulo = "Histórico de tudo que entrou e saiu (últimos 500 lançamentos). Não é editável: serve para conferir."
    colunas = ["Data", "Tipo", "Item", "Quantidade", "Custo unit.", "Documento", "Observação"]
    numericas = (3, 4)
    coluna_esticada = 2
    mensagem_vazia = "Ainda não há movimentações."

    def linhas(self, s):
        saida = []
        for m in estoque.listar_movimentos(s):
            item = m.insumo or m.produto
            unidade = m.insumo.unidade if m.insumo else "un"
            sinal = "+" if m.quantidade > 0 else ""
            doc = m.documento.replace("COMPRA:", "Compra ").replace("PRODUCAO:", "Produção ").replace("VENDA:", "Venda ")
            saida.append((m.id, [m.data.strftime("%d/%m/%Y"), NOMES_TIPO.get(m.tipo, m.tipo), item.nome,
                                 f"{sinal}{num(m.quantidade)} {unidade}", f"R$ {m.custo_unitario:.4f}".replace(".", ","),
                                 doc, m.observacao], "ok" if m.quantidade > 0 else None))
        return saida
