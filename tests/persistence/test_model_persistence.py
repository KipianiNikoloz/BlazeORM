import pytest

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import IntegerField, Model, StringField
from blazeorm.persistence import Session


class Account(Model):
    name = StringField(nullable=False)
    balance = IntegerField(default=0)


class AssignedAccount(Model):
    account_id = IntegerField(primary_key=True)
    name = StringField(nullable=False)


def make_session(tmp_path, name="models.db", *, autocommit=False):
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / name}")
    session = Session(SQLiteAdapter(), connection_config=config, autocommit=autocommit)
    session.execute(
        'CREATE TABLE IF NOT EXISTS "account" '
        '(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, balance INTEGER)'
    )
    session.execute(
        'CREATE TABLE IF NOT EXISTS "assigned_account" '
        '(account_id INTEGER PRIMARY KEY, name TEXT NOT NULL)'
    )
    return session


def test_save_new_instance_with_explicit_session(tmp_path):
    session = make_session(tmp_path)
    account = Account(name="Ada", balance=10)

    account.save(session=session)
    session.commit()

    assert account.id == 1
    assert account._persisted is True
    assert session.execute('SELECT name FROM "account" WHERE id = 1').fetchone()[0] == "Ada"


def test_save_new_assigned_primary_key_inserts(tmp_path):
    session = make_session(tmp_path)
    account = AssignedAccount(account_id=42, name="Grace")

    account.save(session=session)
    session.commit()

    assert session.execute(
        'SELECT name FROM "assigned_account" WHERE account_id = 42'
    ).fetchone()[0] == "Grace"


def test_save_loaded_instance_updates(tmp_path):
    session = make_session(tmp_path)
    account = Account(name="Linus", balance=5)
    account.save(session=session)
    session.commit()
    loaded = session.get(Account, id=account.id)

    loaded.balance = 12
    loaded.save(session=session)
    session.commit()

    assert session.execute('SELECT balance FROM "account" WHERE id = 1').fetchone()[0] == 12


def test_save_uses_context_bound_session(tmp_path):
    session = make_session(tmp_path)
    with session:
        account = Account(name="Margaret")
        account.save()

    verifier = make_session(tmp_path, "models.db")
    assert verifier.execute('SELECT COUNT(*) FROM "account"').fetchone()[0] == 1


def test_save_update_honors_autocommit(tmp_path):
    session = make_session(tmp_path, autocommit=True)
    account = Account(name="Ken", balance=1)
    account.save(session=session)
    account.balance = 2

    account.save(session=session)

    assert session.execute('SELECT balance FROM "account" WHERE id = 1').fetchone()[0] == 2


def test_delete_persisted_instance(tmp_path):
    session = make_session(tmp_path)
    account = Account(name="Dennis")
    account.save(session=session)
    session.commit()

    account.delete(session=session)
    session.commit()

    assert account._persisted is False
    assert session.execute('SELECT COUNT(*) FROM "account"').fetchone()[0] == 0


def test_delete_new_instance_is_rejected(tmp_path):
    session = make_session(tmp_path)

    with pytest.raises(ValueError, match="has not been persisted"):
        Account(name="New").delete(session=session)


@pytest.mark.parametrize("method_name", ["save", "delete"])
def test_instance_persistence_requires_session(method_name):
    account = Account(name="Unbound")
    if method_name == "delete":
        account._persisted = True

    with pytest.raises(RuntimeError, match="requires an active Session"):
        getattr(account, method_name)()
