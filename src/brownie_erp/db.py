"""Engine, sessões, migrações e backup."""
from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from . import config

_engine: Engine | None = None
_Session: sessionmaker[Session] | None = None


def make_engine(url: str) -> Engine:
    engine = create_engine(url, future=True)

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def migrate(url: str) -> None:
    """Aplica as migrações do Alembic até a versão mais recente."""
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def init(path: Path | None = None) -> Engine:
    """Inicializa o banco do aplicativo (cria/atualiza o esquema)."""
    global _engine, _Session
    url = f"sqlite:///{path or config.db_path()}"
    migrate(url)
    _engine = make_engine(url)
    _Session = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def use_engine(engine: Engine) -> None:
    """Usa um engine já criado (testes)."""
    global _engine, _Session
    _engine = engine
    _Session = sessionmaker(engine, expire_on_commit=False)


@contextmanager
def session_scope():
    """Uma transação por operação: confirma no sucesso, desfaz em qualquer erro."""
    if _Session is None:
        raise RuntimeError("Banco não inicializado. Chame db.init() primeiro.")
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def backup(manter: int = 15) -> Path | None:
    """Copia o banco para a pasta de backups (usa a API de backup do SQLite) e poda os antigos."""
    origem = config.db_path()
    if not origem.exists():
        return None
    destino = config.backup_dir() / f"brownie-{datetime.now():%Y%m%d-%H%M%S}.db"
    with sqlite3.connect(origem) as src, sqlite3.connect(destino) as dst:
        src.backup(dst)
    antigos = sorted(config.backup_dir().glob("brownie-*.db"))[:-manter]
    for arq in antigos:
        arq.unlink(missing_ok=True)
    return destino
