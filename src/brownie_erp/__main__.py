from __future__ import annotations

import sys

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from . import APP_NAME, db
from .ui import theme
from .ui.main_window import MainWindow
from .ui.widgets import PT_BR


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    QLocale.setDefault(PT_BR)
    theme.apply_theme(app)

    db.init()
    if "--demo" in argv:
        from .demo import banco_vazio, carregar_exemplo

        with db.session_scope() as s:
            if banco_vazio(s):
                carregar_exemplo(s)

    janela = MainWindow()
    janela.show()
    app.aboutToQuit.connect(db.backup)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
