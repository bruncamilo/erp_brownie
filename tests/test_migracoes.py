from sqlalchemy import create_engine, inspect

from brownie_erp import db
from brownie_erp.models import Base


def test_migracoes_criam_o_mesmo_esquema_dos_modelos(tmp_path):
    url = f"sqlite:///{tmp_path / 'teste.db'}"
    db.migrate(url)
    inspetor = inspect(create_engine(url))
    tabelas = set(inspetor.get_table_names()) - {"alembic_version"}
    assert tabelas == set(Base.metadata.tables)
    for nome, tabela in Base.metadata.tables.items():
        assert {c["name"] for c in inspetor.get_columns(nome)} == {c.name for c in tabela.columns}
