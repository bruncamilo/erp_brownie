"""Diálogos de cadastro e de lançamento. Cada um valida via serviços e mostra o erro dentro da janela."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout,
)
from sqlalchemy import select

from .. import db
from ..errors import RegraDeNegocio
from ..models import CATEGORIAS_DESPESA, FORMAS_PAGAMENTO, UNIDADES, Fornecedor, Insumo, Produto
from ..money import ZERO, D, brl, num, pct
from ..services import cadastros, compras, despesas, estoque, precificacao, producao, vendas
from . import widgets as w


class FormDialog(QDialog):
    """Base: formulário + mensagem de erro + Salvar/Cancelar. Subclasses implementam submit()."""

    def __init__(self, parent, titulo: str, ok: str = "Salvar", largura: int = 440):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(largura)
        self.raiz = QVBoxLayout(self)
        self.raiz.setContentsMargins(22, 20, 22, 18)
        self.raiz.setSpacing(12)
        self.raiz.addWidget(w.rotulo(titulo, "SecaoTitulo"))
        self.form = QFormLayout()
        self.form.setSpacing(10)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.raiz.addLayout(self.form)
        self.mensagem = w.rotulo("", "Erro")
        self.mensagem.hide()
        rodape = QHBoxLayout()
        rodape.addStretch(1)
        rodape.addWidget(w.botao("Cancelar", self.reject))
        self.btn_ok = w.botao(ok, self.accept, primario=True)
        rodape.addWidget(self.btn_ok)
        self._rodape = rodape

    def fechar_layout(self) -> None:
        """Chamar depois de montar o conteúdo: adiciona mensagem de erro e botões ao fim."""
        self.raiz.addWidget(self.mensagem)
        self.raiz.addLayout(self._rodape)

    def submit(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def accept(self) -> None:
        try:
            self.submit()
        except RegraDeNegocio as e:
            self.mensagem.setText(str(e))
            self.mensagem.show()
            return
        super().accept()


# --- Insumos ----------------------------------------------------------------
class InsumoDialog(FormDialog):
    def __init__(self, parent, insumo_id: int | None = None):
        super().__init__(parent, "Novo insumo" if insumo_id is None else "Editar insumo")
        self.insumo_id = insumo_id
        self.nome = QLineEdit()
        self.nome.setPlaceholderText("Ex.: Chocolate meio amargo")
        self.unidade = w.combo([(u, u) for u in UNIDADES])
        self.minimo = w.qtd_spin()
        if insumo_id:
            with db.session_scope() as s:
                i = s.get(Insumo, insumo_id)
                self.nome.setText(i.nome)
                self.unidade.setCurrentIndex(self.unidade.findData(i.unidade))
                self.minimo.setValue(float(i.estoque_minimo))
        self.form.addRow("Nome", self.nome)
        self.form.addRow("Unidade de medida", self.unidade)
        self.form.addRow("Estoque mínimo", self.minimo)
        self.raiz.addWidget(w.rotulo("Quando o saldo chegar no mínimo, o insumo aparece em \"Precisa de atenção\" no início. "
                                     "Use 0 para não receber alerta.", "Suave"))
        self.fechar_layout()

    def submit(self) -> None:
        with db.session_scope() as s:
            if self.insumo_id is None:
                cadastros.criar_insumo(s, self.nome.text(), self.unidade.currentData(), w.dec(self.minimo))
            else:
                cadastros.atualizar_insumo(s, self.insumo_id, self.nome.text(), self.unidade.currentData(), w.dec(self.minimo))


# --- Fornecedores -----------------------------------------------------------
class FornecedorDialog(FormDialog):
    def __init__(self, parent, fornecedor_id: int | None = None):
        super().__init__(parent, "Novo fornecedor" if fornecedor_id is None else "Editar fornecedor")
        self.fornecedor_id = fornecedor_id
        self.nome, self.telefone, self.obs = QLineEdit(), QLineEdit(), QLineEdit()
        if fornecedor_id:
            with db.session_scope() as s:
                f = s.get(Fornecedor, fornecedor_id)
                self.nome.setText(f.nome)
                self.telefone.setText(f.telefone)
                self.obs.setText(f.observacao)
        self.form.addRow("Nome", self.nome)
        self.form.addRow("Telefone", self.telefone)
        self.form.addRow("Observação", self.obs)
        self.fechar_layout()

    def submit(self) -> None:
        with db.session_scope() as s:
            if self.fornecedor_id is None:
                cadastros.criar_fornecedor(s, self.nome.text(), self.telefone.text(), self.obs.text())
            else:
                cadastros.atualizar_fornecedor(s, self.fornecedor_id, self.nome.text(), self.telefone.text(), self.obs.text())


# --- Produtos ---------------------------------------------------------------
class ProdutoDialog(FormDialog):
    def __init__(self, parent, produto_id: int | None = None):
        super().__init__(parent, "Novo produto" if produto_id is None else "Editar produto")
        self.produto_id = produto_id
        self.nome, self.categoria = QLineEdit(), QLineEdit()
        self.nome.setPlaceholderText("Ex.: Brownie tradicional")
        self.categoria.setPlaceholderText("Ex.: Brownies, Caixas, Kits")
        self.preco, self.rendimento, self.minimo = w.money_spin(), w.qtd_spin(0), w.qtd_spin(0)
        self.rendimento.setValue(1)
        if produto_id:
            with db.session_scope() as s:
                p = s.get(Produto, produto_id)
                self.nome.setText(p.nome)
                self.categoria.setText(p.categoria)
                self.preco.setValue(float(p.preco_venda))
                self.rendimento.setValue(float(p.rendimento))
                self.minimo.setValue(float(p.estoque_minimo))
        self.form.addRow("Nome", self.nome)
        self.form.addRow("Categoria", self.categoria)
        self.form.addRow("Preço de venda", self.preco)
        self.form.addRow("Rendimento por lote", self.rendimento)
        self.form.addRow("Estoque mínimo", self.minimo)
        self.raiz.addWidget(w.rotulo("Rendimento é quantas unidades uma receita completa (um lote) produz. "
                                     "A ficha técnica é cadastrada depois, na lista de produtos.", "Suave"))
        self.fechar_layout()

    def submit(self) -> None:
        args = dict(nome=self.nome.text(), preco_venda=w.dec(self.preco), rendimento=w.dec(self.rendimento),
                    categoria=self.categoria.text(), estoque_minimo=w.dec(self.minimo))
        with db.session_scope() as s:
            if self.produto_id is None:
                cadastros.criar_produto(s, **args)
            else:
                cadastros.atualizar_produto(s, self.produto_id, **args)


class FichaDialog(FormDialog):
    """Ficha técnica: ingredientes de UM lote, com o custo calculado ao vivo."""

    def __init__(self, parent, produto_id: int):
        super().__init__(parent, "Ficha técnica", largura=640)
        self.produto_id = produto_id
        with db.session_scope() as s:
            p = s.get(Produto, produto_id)
            self.nome_produto, self.rendimento, self.preco = p.nome, p.rendimento, p.preco_venda
            insumos = list(s.scalars(select(Insumo).where(Insumo.ativo.is_(True)).order_by(Insumo.nome)))
            self.custos = {i.id: i.custo_medio for i in insumos}
            opcoes = [(i.id, f"{i.nome} ({i.unidade})") for i in insumos]
            atuais = [{"insumo_id": f.insumo_id, "quantidade": f.quantidade} for f in p.ficha]
        self.raiz.insertWidget(1, w.rotulo(f"{self.nome_produto} — ingredientes de 1 lote (rende {num(self.rendimento)} un)", "Suave"))
        if not opcoes:
            self.raiz.addWidget(w.rotulo("Cadastre insumos antes de montar a ficha.", "Aviso"))
        self.editor = w.LinhasEditor(
            [{"chave": "insumo_id", "titulo": "Insumo", "tipo": "combo"},
             {"chave": "quantidade", "titulo": "Quantidade por lote", "tipo": "qtd", "casas": 3}],
            opcoes, texto_adicionar="Adicionar ingrediente")
        self.editor.tabela.setMinimumHeight(290)
        self.raiz.addWidget(self.editor)
        self.resumo = w.rotulo("", "Suave")
        self.raiz.addWidget(self.resumo)
        self.editor.definir_linhas(atuais)
        self.editor.alterado.connect(self._recalcular)
        self._recalcular()
        self.fechar_layout()

    def _recalcular(self) -> None:
        total = sum((l["quantidade"] * self.custos.get(l["insumo_id"], ZERO) for l in self.editor.linhas()), ZERO)
        unit = total / self.rendimento if self.rendimento else ZERO
        margem = precificacao.margem_percentual(self.preco, unit)
        texto = f"Custo do lote: {brl(total)}   ·   por unidade: {brl(unit)}"
        if margem is not None:
            texto += f"   ·   margem com o preço atual ({brl(self.preco)}): {pct(margem)}"
        self.resumo.setText(texto + "\nO custo usa o custo médio atual de cada insumo (vem das compras).")

    def submit(self) -> None:
        with db.session_scope() as s:
            cadastros.salvar_ficha(s, self.produto_id, self.editor.linhas())


# --- Ajuste / perda de estoque ----------------------------------------------
class AjusteDialog(FormDialog):
    def __init__(self, parent, item_tipo: str, item_id: int):
        super().__init__(parent, "Ajustar estoque")
        self.item_tipo, self.item_id = item_tipo, item_id
        with db.session_scope() as s:
            item = s.get(Insumo if item_tipo == estoque.INSUMO else Produto, item_id)
            self.saldo, nome = item.estoque_atual, item.nome
            self.unidade = getattr(item, "unidade", "un")
        self.form.addRow("Item", w.rotulo(f"{nome} — saldo atual {num(self.saldo)} {self.unidade}"))
        self.modo = w.combo([("contagem", "Contagem de estoque (informar o saldo real)"),
                             ("perda", "Perda ou descarte (informar o que saiu)")])
        self.quantidade = w.qtd_spin()
        self.quantidade.setValue(float(self.saldo))
        self.motivo = QLineEdit()
        self.motivo.setPlaceholderText("Ex.: contei na prateleira, venceu, caiu no chão")
        self.modo.currentIndexChanged.connect(self._modo)
        self.form.addRow("Tipo", self.modo)
        self.rotulo_qtd = QLabel("Saldo real")
        self.form.addRow(self.rotulo_qtd, self.quantidade)
        self.form.addRow("Motivo", self.motivo)
        self.fechar_layout()

    def _modo(self) -> None:
        contagem = self.modo.currentData() == "contagem"
        self.rotulo_qtd.setText("Saldo real" if contagem else "Quantidade perdida")
        self.quantidade.setValue(float(self.saldo) if contagem else 0)

    def submit(self) -> None:
        with db.session_scope() as s:
            if self.modo.currentData() == "contagem":
                estoque.ajustar_inventario(s, self.item_tipo, self.item_id, w.dec(self.quantidade), date.today(), self.motivo.text())
            else:
                estoque.registrar_perda(s, self.item_tipo, self.item_id, w.dec(self.quantidade), date.today(), self.motivo.text())


# --- Compras ----------------------------------------------------------------
class CompraDialog(FormDialog):
    def __init__(self, parent):
        super().__init__(parent, "Nova compra de insumos", ok="Registrar compra", largura=700)
        with db.session_scope() as s:
            insumos = list(s.scalars(select(Insumo).where(Insumo.ativo.is_(True)).order_by(Insumo.nome)))
            fornecedores = list(s.scalars(select(Fornecedor).where(Fornecedor.ativo.is_(True)).order_by(Fornecedor.nome)))
            opcoes = [(i.id, f"{i.nome} ({i.unidade})") for i in insumos]
            opcoes_forn = [(None, "Sem fornecedor")] + [(f.id, f.nome) for f in fornecedores]
        self.data = w.date_edit()
        self.fornecedor = w.combo(opcoes_forn)
        self.obs = QLineEdit()
        self.form.addRow("Data", self.data)
        self.form.addRow("Fornecedor", self.fornecedor)
        self.form.addRow("Observação", self.obs)
        if not opcoes:
            self.raiz.addWidget(w.rotulo("Cadastre os insumos antes de lançar uma compra.", "Aviso"))
        self.editor = w.LinhasEditor(
            [{"chave": "insumo_id", "titulo": "Insumo", "tipo": "combo"},
             {"chave": "quantidade", "titulo": "Quantidade comprada", "tipo": "qtd", "casas": 3},
             {"chave": "valor_total", "titulo": "Valor pago (total)", "tipo": "money"}], opcoes)
        self.raiz.addWidget(self.editor)
        self.total = w.rotulo("", "SecaoTitulo")
        self.raiz.addWidget(self.total)
        self.raiz.addWidget(w.rotulo("Informe o valor total pago pela quantidade (ex.: 2 kg de chocolate por R$ 56,00 → "
                                     "quantidade 2000 g, valor R$ 56,00 se o insumo estiver em gramas).", "Suave"))
        self.editor.alterado.connect(self._total)
        self.editor.adicionar()
        self.fechar_layout()

    def _total(self) -> None:
        self.total.setText(f"Total da compra: {brl(sum((l['valor_total'] for l in self.editor.linhas()), ZERO))}")

    def submit(self) -> None:
        with db.session_scope() as s:
            compras.registrar_compra(s, data=w.to_date(self.data), itens=self.editor.linhas(),
                                     fornecedor_id=self.fornecedor.currentData(), observacao=self.obs.text())


# --- Produção ---------------------------------------------------------------
class ProducaoDialog(FormDialog):
    def __init__(self, parent):
        super().__init__(parent, "Nova produção", ok="Registrar produção", largura=640)
        with db.session_scope() as s:
            produtos = list(s.scalars(select(Produto).where(Produto.ativo.is_(True)).order_by(Produto.nome)))
            opcoes = [(p.id, p.nome) for p in produtos]
        self.data = w.date_edit()
        self.produto = w.combo(opcoes)
        self.lotes = w.qtd_spin(2)
        self.lotes.setValue(1)
        self.obs = QLineEdit()
        self.form.addRow("Data", self.data)
        self.form.addRow("Produto", self.produto)
        self.form.addRow("Lotes produzidos", self.lotes)
        self.form.addRow("Observação", self.obs)
        self.tabela = w.make_table(["Insumo", "Necessário", "Em estoque", "Situação"])
        self.tabela.setMinimumHeight(150)
        self.raiz.addWidget(self.tabela)
        self.resumo = w.rotulo("", "SecaoTitulo")
        self.raiz.addWidget(self.resumo)
        self.produto.currentIndexChanged.connect(self._atualizar)
        self.lotes.valueChanged.connect(self._atualizar)
        self._atualizar()
        self.fechar_layout()

    def _atualizar(self) -> None:
        pid = self.produto.currentData()
        if pid is None:
            self.resumo.setText("Cadastre um produto para registrar produções.")
            return
        lotes = w.dec(self.lotes)
        with db.session_scope() as s:
            p = s.get(Produto, pid)
            if not p.ficha:
                self.tabela.setRowCount(0)
                self.resumo.setText("Este produto ainda não tem ficha técnica.")
                self.btn_ok.setEnabled(False)
                return
            needs = producao.necessidades(p, lotes)
            linhas = [(n.insumo_id, [n.insumo, f"{num(n.necessario)} {n.unidade}", f"{num(n.disponivel)} {n.unidade}",
                                     "Ok" if n.falta == 0 else f"Faltam {num(n.falta)} {n.unidade}"],
                       None if n.falta == 0 else "alerta") for n in needs]
            custo = sum((n.custo for n in needs), ZERO)
            qtd = p.rendimento * lotes
        w.fill_table(self.tabela, linhas)
        ok = all(n.falta == 0 for n in needs) and lotes > 0
        self.btn_ok.setEnabled(ok)
        unit = custo / qtd if qtd else ZERO
        self.resumo.setText(f"Gera {num(qtd)} un   ·   custo {brl(custo)}   ·   {brl(unit)} por unidade")

    def submit(self) -> None:
        with db.session_scope() as s:
            producao.registrar_producao(s, data=w.to_date(self.data), produto_id=self.produto.currentData(),
                                        lotes=w.dec(self.lotes), observacao=self.obs.text())


# --- Vendas -----------------------------------------------------------------
class VendaDialog(FormDialog):
    def __init__(self, parent):
        super().__init__(parent, "Nova venda", ok="Registrar venda", largura=680)
        with db.session_scope() as s:
            produtos = list(s.scalars(select(Produto).where(Produto.ativo.is_(True)).order_by(Produto.nome)))
            opcoes = [(p.id, f"{p.nome} — {num(p.estoque_atual)} un em estoque") for p in produtos]
            self.precos = {p.id: p.preco_venda for p in produtos}
            self.custos = {p.id: p.custo_medio for p in produtos}
        self.data = w.date_edit()
        self.cliente = QLineEdit()
        self.cliente.setPlaceholderText("Opcional")
        self.forma = w.combo([(f, f) for f in FORMAS_PAGAMENTO])
        self.form.addRow("Data", self.data)
        self.form.addRow("Cliente", self.cliente)
        self.form.addRow("Pagamento", self.forma)
        if not opcoes:
            self.raiz.addWidget(w.rotulo("Cadastre um produto e registre uma produção antes de vender.", "Aviso"))
        self.editor = w.LinhasEditor(
            [{"chave": "produto_id", "titulo": "Produto", "tipo": "combo"},
             {"chave": "quantidade", "titulo": "Qtd.", "tipo": "qtd", "casas": 0},
             {"chave": "preco_unitario", "titulo": "Preço unitário", "tipo": "money"}],
            opcoes, autopreencher=lambda pid: {"preco_unitario": self.precos.get(pid, ZERO), "quantidade": 1})
        self.raiz.addWidget(self.editor)
        linha = QFormLayout()
        self.desconto = w.money_spin()
        linha.addRow("Desconto", self.desconto)
        self.raiz.addLayout(linha)
        self.total = w.rotulo("", "SecaoTitulo")
        self.raiz.addWidget(self.total)
        self.editor.alterado.connect(self._total)
        self.desconto.valueChanged.connect(self._total)
        self.editor.adicionar()
        self.fechar_layout()

    def _total(self) -> None:
        itens = self.editor.linhas()
        subtotal = sum((i["quantidade"] * i["preco_unitario"] for i in itens), ZERO)
        custo = sum((i["quantidade"] * self.custos.get(i["produto_id"], ZERO) for i in itens), ZERO)
        liquido = subtotal - w.dec(self.desconto)
        self.total.setText(f"Total: {brl(liquido)}   ·   lucro estimado: {brl(liquido - custo)}")

    def submit(self) -> None:
        with db.session_scope() as s:
            vendas.registrar_venda(s, data=w.to_date(self.data), itens=self.editor.linhas(), cliente=self.cliente.text(),
                                   forma_pagamento=self.forma.currentData(), desconto=w.dec(self.desconto))


# --- Despesas ---------------------------------------------------------------
class DespesaDialog(FormDialog):
    def __init__(self, parent):
        super().__init__(parent, "Nova despesa", ok="Registrar despesa")
        self.data = w.date_edit()
        self.descricao = QLineEdit()
        self.descricao.setPlaceholderText("Ex.: Botijão de gás")
        self.categoria = QComboBox()
        self.categoria.setEditable(True)
        self.categoria.addItems(CATEGORIAS_DESPESA)
        self.valor = w.money_spin()
        self.form.addRow("Data", self.data)
        self.form.addRow("Descrição", self.descricao)
        self.form.addRow("Categoria", self.categoria)
        self.form.addRow("Valor", self.valor)
        self.raiz.addWidget(w.rotulo("Compras de ingredientes não entram aqui: registre em Compras, para o estoque "
                                     "e o custo dos produtos ficarem corretos.", "Suave"))
        self.fechar_layout()

    def submit(self) -> None:
        with db.session_scope() as s:
            despesas.registrar_despesa(s, data=w.to_date(self.data), descricao=self.descricao.text(),
                                       valor=w.dec(self.valor), categoria=self.categoria.currentText())
