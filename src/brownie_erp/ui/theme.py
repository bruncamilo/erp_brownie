"""Identidade visual: cacau escuro + framboesa, com pistache para o que é positivo.

Evita o par "creme + terracota" que virou lugar-comum: a superfície é um cinza neutro e
a cor de destaque vem de um ingrediente clássico de brownie (framboesa).
"""
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

CACAU = "#2A1A16"
CACAU_2 = "#3B2620"
FRAMBOESA = "#A3214A"
FRAMBOESA_CLARA = "#F3DCE4"
PISTACHE = "#4F7A5A"
AMBAR = "#B7791F"
PERIGO = "#B3261E"
SUPERFICIE = "#F4F3F1"
CARTAO = "#FFFFFF"
LINHA = "#E4DFDB"
TEXTO = "#2A1A16"
TEXTO_SUAVE = "#7A6F6B"

FONTE_CORPO = '"Segoe UI", "Inter", "Helvetica Neue", "Noto Sans", sans-serif'
FONTE_TITULO = 'Georgia, "Noto Serif", "DejaVu Serif", serif'

QSS = f"""
* {{ font-family: {FONTE_CORPO}; font-size: 13px; color: {TEXTO}; }}
QMainWindow, QDialog, #Conteudo {{ background: {SUPERFICIE}; }}

#Sidebar {{ background: {CACAU}; }}
#Marca {{ font-family: {FONTE_TITULO}; font-size: 19px; color: #F6EDE8; padding: 4px 4px 0 4px; }}
#MarcaSub {{ color: #A99A94; font-size: 12px; padding: 0 4px 10px 4px; }}
#Sidebar QPushButton {{
    text-align: left; padding: 9px 14px; border: none; border-left: 3px solid transparent;
    border-radius: 0; color: #D8CBC5; background: transparent; font-size: 13px;
}}
#Sidebar QPushButton:hover {{ background: {CACAU_2}; }}
#Sidebar QPushButton:checked {{ background: {CACAU_2}; border-left: 3px solid {FRAMBOESA}; color: #FFFFFF; font-weight: 600; }}
#Separador {{ background: #4A332C; max-height: 1px; min-height: 1px; margin: 8px 14px; }}

#TituloPagina {{ font-family: {FONTE_TITULO}; font-size: 26px; color: {TEXTO}; }}
#Subtitulo {{ color: {TEXTO_SUAVE}; }}
#SecaoTitulo {{ font-family: {FONTE_TITULO}; font-size: 16px; }}
#Suave {{ color: {TEXTO_SUAVE}; }}
#Erro {{ color: {PERIGO}; background: #FBEAE8; border-radius: 6px; padding: 8px 10px; }}
#Aviso {{ color: #7A5412; background: #FBF1DC; border-radius: 6px; padding: 8px 10px; }}

QPushButton {{
    background: {CARTAO}; border: 1px solid #CFC8C3; border-radius: 6px; padding: 7px 14px;
}}
QPushButton:hover {{ background: #FAF8F7; border-color: #B9B0AA; }}
QPushButton:disabled {{ color: #B0A7A2; background: #F0EEEC; }}
QPushButton[primary="true"] {{ background: {FRAMBOESA}; border-color: {FRAMBOESA}; color: #FFFFFF; font-weight: 600; }}
QPushButton[primary="true"]:hover {{ background: #8C1B3F; }}
QPushButton[perigo="true"] {{ color: {PERIGO}; }}

QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateEdit, QPlainTextEdit {{
    background: {CARTAO}; border: 1px solid #CFC8C3; border-radius: 6px; padding: 6px 8px; min-height: 18px;
    selection-background-color: {FRAMBOESA};
}}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QDateEdit:focus {{ border: 1px solid {FRAMBOESA}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {CARTAO}; selection-background-color: {FRAMBOESA_CLARA}; selection-color: {TEXTO}; }}

QTableWidget {{
    background: {CARTAO}; border: 1px solid {LINHA}; border-radius: 8px; gridline-color: transparent;
    alternate-background-color: #FBFAF9; selection-background-color: {FRAMBOESA_CLARA}; selection-color: {TEXTO};
}}
QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid #F0ECE9; }}
QHeaderView::section {{
    background: {CARTAO}; color: {TEXTO_SUAVE}; font-weight: 600; border: none;
    border-bottom: 1px solid {LINHA}; padding: 8px; text-align: left;
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ width: 0px; border: none; }}
QAbstractSpinBox QLineEdit, QComboBox QLineEdit {{ border: none; padding: 0; min-height: 0; background: transparent; }}
QTableWidget QDoubleSpinBox, QTableWidget QComboBox {{ margin: 3px 4px; padding: 3px 8px; min-height: 22px; }}
QTableCornerButton::section {{ background: {CARTAO}; border: none; }}

#Faixa {{ background: {CARTAO}; border: 1px solid {LINHA}; border-radius: 8px; }}
#FaixaDivisor {{ background: {LINHA}; min-width: 1px; max-width: 1px; }}
#FaixaRotulo {{ color: {TEXTO_SUAVE}; }}
#FaixaValor {{ font-family: {FONTE_TITULO}; font-size: 24px; }}
#Painel {{ background: {CARTAO}; border: 1px solid {LINHA}; border-radius: 8px; }}
#Painel QTableWidget {{ border: none; border-radius: 0; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #D5CDC8; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QToolTip {{ background: {CACAU}; color: #FFFFFF; border: none; padding: 5px; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(QSS)
