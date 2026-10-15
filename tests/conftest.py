from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from brownie_erp.models import Base


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    s = sessionmaker(engine, expire_on_commit=False)()
    yield s
    s.close()


HOJE = date(2026, 10, 11)


@pytest.fixture()
def cenario(session):
    """Confeitaria mínima: 2 insumos, 1 produto com ficha, tudo sem estoque."""
    from brownie_erp.services import cadastros

    chocolate = cadastros.criar_insumo(session, "Chocolate meio amargo", "g", 500)
    ovos = cadastros.criar_insumo(session, "Ovos", "un", 6)
    brownie = cadastros.criar_produto(session, "Brownie tradicional", 9, rendimento=12, estoque_minimo=10)
    cadastros.salvar_ficha(session, brownie.id, [
        {"insumo_id": chocolate.id, "quantidade": 400},   # por lote
        {"insumo_id": ovos.id, "quantidade": 4},
    ])
    session.commit()
    return {"chocolate": chocolate, "ovos": ovos, "brownie": brownie}
