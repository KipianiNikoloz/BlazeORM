from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import ManyToManyField, Model, StringField
from blazeorm.dialects import SQLiteDialect
from blazeorm.persistence import Session
from blazeorm.schema import MigrationEngine, MigrationOperation, SchemaBuilder


class User(Model):
    name = StringField(nullable=False)


class Group(Model):
    name = StringField(nullable=False)
    members = ManyToManyField(User, related_name="groups")


def create_tables(session: Session):
    builder = SchemaBuilder(SQLiteDialect())
    ops = [
        MigrationOperation(sql=builder.create_table_sql(User)),
        MigrationOperation(sql=builder.create_table_sql(Group)),
    ]
    ops.extend(MigrationOperation(sql=stmt) for stmt in builder.create_many_to_many_sql(Group))
    engine = MigrationEngine(session.adapter, session.dialect)
    engine.apply("app", "0001", ops)


def test_many_to_many_add_and_fetch(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'm2m.db'}")
    session = Session(adapter, connection_config=config)
    create_tables(session)

    user = User(name="Alice")
    group = Group(name="Admins")
    session.begin()
    session.add(user)
    session.add(group)
    session.commit()

    # Manually insert into through table
    through = f"{group._meta.table_name}_{user._meta.table_name}"
    session.execute(
        f'INSERT INTO "{through}" (group_id, user_id) VALUES (?, ?)',
        (group.id, user.id),
    )

    with session:
        groups = list(User.objects.prefetch_related("groups"))
    assert groups[0].groups[0].name == "Admins"


def test_many_to_many_manager_add_remove_clear(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'ops.db'}")
    session = Session(adapter, connection_config=config)
    create_tables(session)

    user = User(name="Alice")
    group = Group(name="Admins")
    session.begin()
    session.add(user)
    session.add(group)
    session.commit()

    with session:
        group.members.add(user)
        members = list(group.members)
        assert len(members) == 1
        assert members[0].name == "Alice"
        # Reverse accessor should work
        assert hasattr(user, "groups")
        user_groups = list(user.groups)
        assert len(user_groups) == 1
        assert user_groups[0].name == "Admins"

        group.members.remove(user)
        assert list(group.members) == []

        group.members.clear()
        assert list(group.members) == []


def test_session_m2m_helpers_invalidate_cache(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'ops_cache.db'}")
    session = Session(adapter, connection_config=config)
    create_tables(session)

    user = User(name="Alice")
    group = Group(name="Admins")
    session.begin()
    session.add(user)
    session.add(group)
    session.commit()

    with session:
        session.add_m2m(group, "members", user)
        # hydrate cache
        cached_members = list(group.members)
        assert cached_members
        assert "members" in group._related_cache
        session.remove_m2m(group, "members", user)
        assert "members" not in group._related_cache
        # identity map retains instance
        assert session.identity_map.get(Group, group.pk) is group

        # use model sugar and ensure cache cleared
        group.m2m_add("members", user, session=session)
        group.m2m_clear("members", session=session)
        assert group._related_cache.get("members") == []
