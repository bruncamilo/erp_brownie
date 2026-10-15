"""Páginas de cadastro: insumos, produtos e fornecedores."""
from __future__ import annotations

from sqlalchemy import select

from ...models import Fornecedor, Insumo, Produto
from ...money import brl, num, pct
from ...services import cadastros, estoque, precificacao, producao
from .. import dialogs
from ..widgets import Page


class InsumosPage(Page):
    titulo = "Insumos"
    subtitulo = "Ingredientes e embalagens. O custo médio é atualizado a cada compra."
    colunas = ["Insumo", "Unidade", "Em estoque", "Mínimo", "Custo médio", "Valor em estoque", "Situação"]
    numericas = (2, 3, 4, 5)
    mensagem_vazia = "Nenhum insumo cadastrado. Comece por \"Novo insumo\"."
    legenda = "Em vermelho: estoque no mínimo ou abaixo dele."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.acao("Novo insumo", self.nova, primario=True)
        self.acao("Editar", self.editar)
        self.acao("Ajustar estoque", self.ajustar)
        self.acao("Inativar ou reativar", self.alternar)

    def linhas(self, s):
        saida = []
        for i in s.scalars(select(Insumo).order_by(Insumo.nome)):
            baixo = i.ativo and i.estoque_minimo > 0 and i.estoque_atual <= i.estoque_minimo
            tom = "suave" if not i.ativo else ("alerta" if baixo else None)
            saida.append((i.id, [i.nome, i.unidade, num(i.estoque_atual), num(i.estoque_minimo),
                                 f"{brl(i.custo_medio)}/{i.unidade}" if i.custo_medio >= 0.01 else
                                 f"R$ {i.custo_medio:.4f}/{i.unidade}".replace(".", ","),
                                 brl(i.estoque_atual * i.custo_medio), "Ativo" if i.ativo else "Inativo"], tom))
        return saida

    def nova(self):
        if dialogs.InsumoDialog(self).exec():
            self.refresh()

    def editar(self):
        rid = self.selecionado()
        if rid and dialogs.InsumoDialog(self, rid).exec():
            self.refresh()

    ao_duplo_clique = editar

    def ajustar(self):
        rid = self.selecionado()
        if rid and dialogs.AjusteDialog(self, estoque.INSUMO, rid).exec():
            self.refresh()

    def alternar(self):
        rid = self.selecionado()
        if rid:
            def op(s):
                i = s.get(Insumo, rid)
                cadastros.definir_insumo_ativo(s, rid, not i.ativo)
            self.executar(op)


class ProdutosPage(Page):
    titulo = "Produtos"
    subtitulo = "O custo vem da ficha técnica e dos custos médios dos insumos."
    colunas = ["Produto", "Categoria", "Preço", "Custo (ficha)", "Margem", "Em estoque", "Situação"]
    numericas = (2, 3, 4, 5)
    mensagem_vazia = "Nenhum produto cadastrado. Comece por \"Novo produto\" e depois monte a ficha técnica."
    legenda = "Em laranja: sem ficha técnica ou estoque no mínimo. Em vermelho: preço de venda abaixo do custo."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.acao("Novo produto", self.nova, primario=True)
        self.acao("Editar", self.editar)
        self.acao("Ficha técnica", self.ficha)
        self.acao("Ajustar estoque", self.ajustar)
        self.acao("Inativar ou reativar", self.alternar)

    def linhas(self, s):
        saida = []
        for p in s.scalars(select(Produto).order_by(Produto.nome)):
            if p.ficha:
                custo = producao.custo_unitario_estimado(p)
                margem = precificacao.margem_percentual(p.preco_venda, custo)
                custo_txt, margem_txt = brl(custo), pct(margem) if margem is not None else "–"
            else:
                custo, margem, custo_txt, margem_txt = None, None, "Sem ficha", "–"
            baixo = p.ativo and p.estoque_minimo > 0 and p.estoque_atual <= p.estoque_minimo
            if not p.ativo:
                tom = "suave"
            elif custo is not None and p.preco_venda < custo:
                tom = "alerta"          # vendendo abaixo do custo
            elif custo is None or baixo:
                tom = "aviso"
            else:
                tom = None
            saida.append((p.id, [p.nome, p.categoria, brl(p.preco_venda), custo_txt, margem_txt,
                                 num(p.estoque_atual), "Ativo" if p.ativo else "Inativo"], tom))
        return saida

    def nova(self):
        if dialogs.ProdutoDialog(self).exec():
            self.refresh()

    def editar(self):
        rid = self.selecionado()
        if rid and dialogs.ProdutoDialog(self, rid).exec():
            self.refresh()

    ao_duplo_clique = editar

    def ficha(self):
        rid = self.selecionado()
        if rid and dialogs.FichaDialog(self, rid).exec():
            self.refresh()

    def ajustar(self):
        rid = self.selecionado()
        if rid and dialogs.AjusteDialog(self, estoque.PRODUTO, rid).exec():
            self.refresh()

    def alternar(self):
        rid = self.selecionado()
        if rid:
            def op(s):
                p = s.get(Produto, rid)
                cadastros.definir_produto_ativo(s, rid, not p.ativo)
            self.executar(op)


class FornecedoresPage(Page):
    titulo = "Fornecedores"
    subtitulo = "Onde você compra. Opcional nas compras, mas ajuda a comparar preços."
    colunas = ["Fornecedor", "Telefone", "Observação", "Situação"]
    mensagem_vazia = "Nenhum fornecedor cadastrado."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.acao("Novo fornecedor", self.nova, primario=True)
        self.acao("Editar", self.editar)
        self.acao("Inativar ou reativar", self.alternar)

    def linhas(self, s):
        return [(f.id, [f.nome, f.telefone, f.observacao, "Ativo" if f.ativo else "Inativo"], None if f.ativo else "suave")
                for f in s.scalars(select(Fornecedor).order_by(Fornecedor.nome))]

    def nova(self):
        if dialogs.FornecedorDialog(self).exec():
            self.refresh()

    def editar(self):
        rid = self.selecionado()
        if rid and dialogs.FornecedorDialog(self, rid).exec():
            self.refresh()

    ao_duplo_clique = editar

    def alternar(self):
        rid = self.selecionado()
        if rid:
            def op(s):
                f = s.get(Fornecedor, rid)
                cadastros.definir_fornecedor_ativo(s, rid, not f.ativo)
            self.executar(op)
