"""Componentes reutilizáveis da interface."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Callable

from PySide6.QtCore import QDate, QLocale, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QAbstractSpinBox, QComboBox, QDateEdit, QDoubleSpinBox, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import db
from ..errors import RegraDeNegocio
from ..money import D, brl
from . import theme

PT_BR = QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
MESES_CURTOS = [m[:3] for m in MESES]


# --- Entradas ---------------------------------------------------------------
def qtd_spin(casas: int = 3, maximo: float = 9_999_999) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setLocale(PT_BR)
    s.setDecimals(casas)
    s.setRange(0, maximo)
    s.setGroupSeparatorShown(True)
    s.setAlignment(Qt.AlignmentFlag.AlignRight)
    return s


def money_spin() -> QDoubleSpinBox:
    s = qtd_spin(2, 9_999_999)
    s.setPrefix("R$ ")
    return s


def date_edit(valor: date | None = None) -> QDateEdit:
    d = QDateEdit()
    d.setLocale(PT_BR)
    d.setCalendarPopup(True)
    d.setDisplayFormat("dd/MM/yyyy")
    d.setDate(QDate(valor.year, valor.month, valor.day) if valor else QDate.currentDate())
    return d


def dec(spin: QDoubleSpinBox) -> Decimal:
    return D(f"{spin.value():.6f}")


def to_date(edit: QDateEdit) -> date:
    return edit.date().toPython()


def combo(opcoes: list[tuple[int | None, str]], atual: int | None = None) -> QComboBox:
    c = QComboBox()
    for valor, rotulo in opcoes:
        c.addItem(rotulo, valor)
    if atual is not None:
        i = c.findData(atual)
        if i >= 0:
            c.setCurrentIndex(i)
    return c


def botao(texto: str, slot: Callable | None = None, primario: bool = False, perigo: bool = False) -> QPushButton:
    b = QPushButton(texto)
    if primario:
        b.setProperty("primary", True)
    if perigo:
        b.setProperty("perigo", True)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if slot:
        b.clicked.connect(lambda _=False: slot())
    return b


def rotulo(texto: str, nome: str = "") -> QLabel:
    l = QLabel(texto)
    if nome:
        l.setObjectName(nome)
    l.setWordWrap(True)
    return l


# --- Tabelas ----------------------------------------------------------------
def make_table(headers: list[str], stretch: int = 0) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(34)
    t.setShowGrid(False)
    t.setAlternatingRowColors(True)
    t.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    head = t.horizontalHeader()
    head.setHighlightSections(False)
    for i in range(len(headers)):
        head.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch if i == stretch
                                  else QHeaderView.ResizeMode.ResizeToContents)
    return t


_TONS = {"alerta": theme.PERIGO, "suave": "#9A8F8A", "ok": theme.PISTACHE, "aviso": theme.AMBAR}


def fill_table(t: QTableWidget, linhas: list[tuple[int | None, list[str], str | None]],
               numericas: tuple[int, ...] = ()) -> None:
    """linhas: (id, células, tom). Tom: 'alerta' | 'suave' | 'ok' | 'aviso' | None."""
    for c in range(t.columnCount()):
        h = t.horizontalHeaderItem(c)
        if h:
            h.setTextAlignment((Qt.AlignmentFlag.AlignRight if c in numericas else Qt.AlignmentFlag.AlignLeft)
                               | Qt.AlignmentFlag.AlignVCenter)
    t.setRowCount(len(linhas))
    for r, (rid, celulas, tom) in enumerate(linhas):
        for c, texto in enumerate(celulas):
            item = QTableWidgetItem(texto)
            if c == 0:
                item.setData(Qt.ItemDataRole.UserRole, rid)
            if c in numericas:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if tom:
                item.setForeground(QColor(_TONS[tom]))
            t.setItem(r, c, item)


def selected_id(t: QTableWidget) -> int | None:
    linhas = t.selectionModel().selectedRows()
    if not linhas:
        return None
    return t.item(linhas[0].row(), 0).data(Qt.ItemDataRole.UserRole)


def erro(parent, e: Exception) -> None:
    QMessageBox.warning(parent, "Não foi possível concluir", str(e))


def confirmar(parent, titulo: str, texto: str, ok: str = "Confirmar") -> bool:
    caixa = QMessageBox(QMessageBox.Icon.Question, titulo, texto, parent=parent)
    sim = caixa.addButton(ok, QMessageBox.ButtonRole.AcceptRole)
    caixa.addButton("Voltar", QMessageBox.ButtonRole.RejectRole)
    caixa.exec()
    return caixa.clickedButton() is sim


# --- Página base ------------------------------------------------------------
class Page(QWidget):
    """Título + barra de ações + busca + tabela. Subclasses definem colunas e `linhas()`."""

    titulo = ""
    subtitulo = ""
    colunas: list[str] = []
    numericas: tuple[int, ...] = ()
    busca = True
    coluna_esticada = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 24)
        raiz.setSpacing(14)

        cabeca = QVBoxLayout()
        cabeca.setSpacing(2)
        cabeca.addWidget(rotulo(self.titulo, "TituloPagina"))
        if self.subtitulo:
            cabeca.addWidget(rotulo(self.subtitulo, "Subtitulo"))
        raiz.addLayout(cabeca)

        self.barra = QHBoxLayout()
        self.barra.setSpacing(8)
        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Buscar")
        self.campo_busca.setClearButtonEnabled(True)
        self.campo_busca.setMaximumWidth(260)
        self.campo_busca.textChanged.connect(self._filtrar)
        if self.busca:
            self.barra.addWidget(self.campo_busca)
        self.barra.addStretch(1)
        raiz.addLayout(self.barra)

        self.tabela = make_table(self.colunas, self.coluna_esticada)
        self.tabela.doubleClicked.connect(lambda _=None: self.ao_duplo_clique())
        raiz.addWidget(self.tabela, 1)

        self.vazio = rotulo("", "Suave")
        self.vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        raiz.addWidget(self.vazio)
        if self.legenda:
            raiz.addWidget(rotulo(self.legenda, "Suave"))

    # ganchos
    def linhas(self, session) -> list[tuple[int | None, list[str], str | None]]:
        return []

    def ao_duplo_clique(self) -> None:
        pass

    mensagem_vazia = "Nada por aqui ainda."
    legenda = ""

    def acao(self, texto: str, slot: Callable, primario: bool = False, perigo: bool = False) -> QPushButton:
        b = botao(texto, slot, primario, perigo)
        self.barra.addWidget(b)
        return b

    def refresh(self) -> None:
        with db.session_scope() as s:
            dados = self.linhas(s)
        fill_table(self.tabela, dados, self.numericas)
        self.vazio.setText(self.mensagem_vazia if not dados else "")
        self.vazio.setVisible(not dados)
        self._filtrar(self.campo_busca.text())

    def _filtrar(self, texto: str) -> None:
        texto = texto.strip().lower()
        for r in range(self.tabela.rowCount()):
            conteudo = " ".join((self.tabela.item(r, c).text() if self.tabela.item(r, c) else "")
                                for c in range(self.tabela.columnCount())).lower()
            self.tabela.setRowHidden(r, bool(texto) and texto not in conteudo)

    def executar(self, fn: Callable, sucesso: bool = True) -> bool:
        """Roda uma operação numa transação, mostrando erros de regra de negócio ao usuário."""
        try:
            with db.session_scope() as s:
                fn(s)
        except RegraDeNegocio as e:
            erro(self, e)
            return False
        if sucesso:
            self.refresh()
        return True

    def selecionado(self, aviso: str = "Selecione uma linha da tabela primeiro.") -> int | None:
        rid = selected_id(self.tabela)
        if rid is None:
            erro(self, RegraDeNegocio(aviso))
        return rid


# --- Faixa de números -------------------------------------------------------
class Faixa(QFrame):
    """Uma única faixa com vários números separados por divisores (em vez de cartões repetidos)."""

    def __init__(self, itens: list[str]):
        super().__init__()
        self.setObjectName("Faixa")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 12)
        self._valores: dict[str, QLabel] = {}
        for i, nome in enumerate(itens):
            if i:
                div = QFrame()
                div.setObjectName("FaixaDivisor")
                lay.addWidget(div)
            col = QVBoxLayout()
            col.setContentsMargins(20, 0, 20, 0)
            col.setSpacing(2)
            col.addWidget(rotulo(nome, "FaixaRotulo"))
            v = QLabel("–")
            v.setObjectName("FaixaValor")
            col.addWidget(v)
            lay.addLayout(col, 1)
            self._valores[nome] = v

    def definir(self, nome: str, texto: str, tom: str | None = None) -> None:
        v = self._valores[nome]
        v.setText(texto)
        cor = {"ok": theme.PISTACHE, "alerta": theme.PERIGO}.get(tom or "", theme.TEXTO)
        v.setStyleSheet(f"color: {cor};")


# --- Gráfico de barras ------------------------------------------------------
class GraficoBarras(QWidget):
    """Barras agrupadas: duas séries por rótulo (ex.: receita x custos por mês)."""

    def __init__(self, nome_a: str, nome_b: str):
        super().__init__()
        self.nomes = (nome_a, nome_b)
        self.dados: list[tuple[str, float, float]] = []
        self.setMinimumHeight(210)

    def definir(self, dados: list[tuple[str, float, float]]) -> None:
        self.dados = dados
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        esq, topo, base = 56, 26, 28
        area = QRectF(esq, topo, w - esq - 8, h - topo - base)
        fonte = QFont(self.font())
        fonte.setPointSizeF(8.5)
        p.setFont(fonte)

        # legenda
        for i, (nome, cor) in enumerate(zip(self.nomes, (theme.FRAMBOESA, "#B9A59E"))):
            x = esq + i * 110
            p.setBrush(QColor(cor))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, 6, 10, 10), 2, 2)
            p.setPen(QColor(theme.TEXTO_SUAVE))
            p.drawText(QRectF(x + 15, 2, 90, 18), Qt.AlignmentFlag.AlignVCenter, nome)

        maximo = max([max(a, b) for _, a, b in self.dados] + [1.0])
        for k in range(4):  # linhas de referência
            y = area.bottom() - area.height() * k / 3
            p.setPen(QPen(QColor(theme.LINHA), 1))
            p.drawLine(int(area.left()), int(y), int(area.right()), int(y))
            p.setPen(QColor(theme.TEXTO_SUAVE))
            valor = maximo * k / 3
            texto = f"{valor/1000:.1f}k".replace(".", ",") if valor >= 1000 else f"{valor:.0f}"
            p.drawText(QRectF(0, y - 9, esq - 8, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, texto)

        n = max(len(self.dados), 1)
        slot = area.width() / n
        larg = min(slot * 0.32, 26)
        for i, (nome, a, b) in enumerate(self.dados):
            cx = area.left() + slot * (i + 0.5)
            for off, val, cor in ((-larg - 1, a, theme.FRAMBOESA), (1, b, "#B9A59E")):
                alt = area.height() * val / maximo
                p.setBrush(QColor(cor))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(cx + off, area.bottom() - alt, larg, max(alt, 0)), 2, 2)
            p.setPen(QColor(theme.TEXTO_SUAVE))
            p.drawText(QRectF(cx - slot / 2, area.bottom() + 4, slot, 18), Qt.AlignmentFlag.AlignHCenter, nome)
        p.end()


# --- Editor de linhas (itens de compra, venda, ficha técnica) ---------------
class LinhasEditor(QWidget):
    """Tabela editável de itens. colunas: [{"chave", "titulo", "tipo": "combo"|"qtd"|"money", "casas"}]."""

    alterado = Signal()

    def __init__(self, colunas: list[dict], opcoes: list[tuple[int, str]], autopreencher: Callable | None = None,
                 texto_adicionar: str = "Adicionar item"):
        super().__init__()
        self.colunas, self.opcoes, self.autopreencher = colunas, opcoes, autopreencher
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.tabela = make_table([c["titulo"] for c in colunas], stretch=0)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setAlternatingRowColors(False)
        self.tabela.setMinimumHeight(190)
        self.tabela.verticalHeader().setDefaultSectionSize(42)
        lay.addWidget(self.tabela)
        barra = QHBoxLayout()
        barra.addWidget(botao(texto_adicionar, self.adicionar))
        barra.addWidget(botao("Remover linha", self.remover))
        barra.addStretch(1)
        lay.addLayout(barra)

    def adicionar(self, valores: dict | None = None) -> None:
        r = self.tabela.rowCount()
        self.tabela.insertRow(r)
        for c, col in enumerate(self.colunas):
            if col["tipo"] == "combo":
                w = combo(self.opcoes)
                w.currentIndexChanged.connect(lambda _=0, w=w: self._combo_mudou(w))
            elif col["tipo"] == "money":
                w = money_spin()
            else:
                w = qtd_spin(col.get("casas", 3))
            if col["tipo"] != "combo":
                w.valueChanged.connect(lambda _=0: self.alterado.emit())
            self.tabela.setCellWidget(r, c, w)
        if valores:
            self._aplicar(r, valores)
        elif self.autopreencher and self.opcoes:
            self._combo_mudou(self.tabela.cellWidget(r, self._coluna_combo()))
        self.alterado.emit()

    def _coluna_combo(self) -> int:
        return next(i for i, c in enumerate(self.colunas) if c["tipo"] == "combo")

    def _aplicar(self, linha: int, valores: dict) -> None:
        for c, col in enumerate(self.colunas):
            if col["chave"] not in valores:
                continue
            w = self.tabela.cellWidget(linha, c)
            if col["tipo"] == "combo":
                w.setCurrentIndex(max(w.findData(valores[col["chave"]]), 0))
            else:
                w.setValue(float(valores[col["chave"]]))

    def _combo_mudou(self, w: QComboBox) -> None:
        if self.autopreencher:
            for r in range(self.tabela.rowCount()):
                if self.tabela.cellWidget(r, self._coluna_combo()) is w:
                    self._aplicar(r, self.autopreencher(w.currentData()))
        self.alterado.emit()

    def remover(self) -> None:
        linhas = self.tabela.selectionModel().selectedRows()
        r = linhas[0].row() if linhas else self.tabela.rowCount() - 1
        if r >= 0:
            self.tabela.removeRow(r)
            self.alterado.emit()

    def definir_linhas(self, linhas: list[dict]) -> None:
        self.tabela.setRowCount(0)
        for v in linhas:
            self.adicionar(v)

    def linhas(self) -> list[dict]:
        saida = []
        for r in range(self.tabela.rowCount()):
            linha = {}
            for c, col in enumerate(self.colunas):
                w = self.tabela.cellWidget(r, c)
                linha[col["chave"]] = w.currentData() if col["tipo"] == "combo" else dec(w)
            saida.append(linha)
        return saida
