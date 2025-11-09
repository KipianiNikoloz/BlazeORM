import pytest

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import IntegerField, Model, StringField
from blazeorm.hooks import hooks
from blazeorm.persistence import Session


@pytest.fixture(autouse=True)
def clear_hooks():
    hooks.clear()
    yield
    hooks.clear()


def make_session(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'hooks.db'}")
    session = Session(adapter, connection_config=config)
    session.execute(
        "CREATE TABLE IF NOT EXISTS \"sample\" (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER)"
    )
    return session


class Sample(Model):
    name = StringField(nullable=False)
    age = IntegerField(default=0)


def test_hooks_fire_in_order(tmp_path):
    events = []

    for event_name in [
        "before_validate",
        "after_validate",
        "before_save",
        "after_save",
        "after_commit",
    ]:
        def handler(inst, event=event_name, **ctx):
            events.append((event, inst.name if inst else None))

        hooks.register(event_name, handler)

    session = make_session(tmp_path)
    session.begin()
    sample = Sample(name="Alice", age=21)
    session.add(sample)
    session.commit()

    assert events[:4] == [
        ("before_validate", "Alice"),
        ("after_validate", "Alice"),
        ("before_save", "Alice"),
        ("after_save", "Alice"),
    ]
    assert events[-1] == ("after_commit", None)
    session.close()


def test_model_specific_hook_on_delete(tmp_path):
    fired = []

    def before_delete(instance, **context):
        fired.append(("before", instance.name))

    def after_delete(instance, **context):
        fired.append(("after", instance.name))

    Sample.register_hook("before_delete", before_delete)
    Sample.register_hook("after_delete", after_delete)

    session = make_session(tmp_path)
    session.begin()
    sample = Sample(name="Bob", age=30)
    session.add(sample)
    session.commit()

    to_delete = session.get(Sample, id=sample.id)
    session.begin()
    session.delete(to_delete)
    session.commit()

    assert fired == [("before", "Bob"), ("after", "Bob")]
    session.close()
