from __future__ import annotations

from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from .. import APP_NAME
from . import widgets as w
from .pages.cadastros import FornecedoresPage, InsumosPage, ProdutosPage
from .pages.movimento import ComprasPage, DespesasPage, MovimentosPage, ProducaoPage, VendasPage
from .pages.painel import InicioPage, ResultadoPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1180, 760)
        self.setMinimumSize(980, 640)

        self.paginas: dict[str, QWidget] = {}
        self.pilha = QStackedWidget()
        self.pilha.setObjectName("Conteudo")

        lateral = QFrame()
        lateral.setObjectName("Sidebar")
        lateral.setFixedWidth(210)
        lay = QVBoxLayout(lateral)
        lay.setContentsMargins(0, 18, 0, 14)
        lay.setSpacing(1)
        lay.addWidget(w.rotulo("Brownies", "Marca"))
        lay.addWidget(w.rotulo("Gestão da confeitaria", "MarcaSub"))

        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)

        def item(chave: str, texto: str, pagina: QWidget) -> None:
            self.paginas[chave] = pagina
            self.pilha.addWidget(pagina)
            b = QPushButton(texto)
            b.setCheckable(True)
            b.setCursor(w.Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=chave: self.ir(c))
            self.grupo.addButton(b)
            lay.addWidget(b)
            pagina.botao_nav = b

        def separador() -> None:
            s = QFrame()
            s.setObjectName("Separador")
            lay.addWidget(s)

        item("inicio", "Início", InicioPage(self.atalho))
        separador()
        item("vendas", "Vendas", VendasPage())
        item("producao", "Produção", ProducaoPage())
        item("compras", "Compras", ComprasPage())
        item("despesas", "Despesas", DespesasPage())
        separador()
        item("produtos", "Produtos", ProdutosPage())
        item("insumos", "Insumos", InsumosPage())
        item("fornecedores", "Fornecedores", FornecedoresPage())
        separador()
        item("estoque", "Movimentação de estoque", MovimentosPage())
        item("resultado", "Resultado", ResultadoPage())
        lay.addStretch(1)

        central = QWidget()
        corpo = QHBoxLayout(central)
        corpo.setContentsMargins(0, 0, 0, 0)
        corpo.setSpacing(0)
        corpo.addWidget(lateral)
        corpo.addWidget(self.pilha, 1)
        self.setCentralWidget(central)
        self.ir("inicio")

    def ir(self, chave: str) -> None:
        pagina = self.paginas[chave]
        self.pilha.setCurrentWidget(pagina)
        pagina.botao_nav.setChecked(True)
        pagina.refresh()

    def atalho(self, chave: str) -> None:
        """Atalho do Início: abre a página e já o diálogo de novo lançamento."""
        self.ir(chave)
        self.paginas[chave].nova()
        self.ir("inicio")
