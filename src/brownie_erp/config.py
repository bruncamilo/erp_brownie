"""Caminhos e configuração. O banco fica numa pasta de dados do usuário, fora do repositório."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def data_dir() -> Path:
    override = os.environ.get("BROWNIE_ERP_DATA")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / "BrownieERP"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "BrownieERP"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "BrownieERP"
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "brownie.db"


def backup_dir() -> Path:
    p = data_dir() / "backups"
    p.mkdir(exist_ok=True)
    return p
