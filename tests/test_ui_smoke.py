"""Abre a janela principal (sem tela, via Qt offscreen) e percorre todas as páginas."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")


def test_janela_abre_e_todas_as_paginas_carregam(tmp_path):
    from PySide6.QtWidgets import QApplication

    from brownie_erp import db
    from brownie_erp.demo import carregar_exemplo
    from brownie_erp.ui import theme
    from brownie_erp.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    theme.apply_theme(app)
    db.init(tmp_path / "ui.db")
    with db.session_scope() as s:
        carregar_exemplo(s)
    janela = MainWindow()
    for chave in janela.paginas:
        janela.ir(chave)
        app.processEvents()
    assert set(janela.paginas) >= {"inicio", "vendas", "producao", "compras", "produtos", "insumos", "resultado"}
    janela.close()
