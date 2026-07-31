import pytest

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import (
    ForeignKey,
    IntegerField,
    ManyToManyField,
    Model,
    ModelConfigurationError,
    OneToOneField,
    StringField,
)
from blazeorm.dialects import SQLiteDialect
from blazeorm.persistence import Session
from blazeorm.schema import SchemaBuilder


def test_concrete_model_inherits_abstract_chain_in_order():
    class AuditFields(Model):
        created_by = StringField(nullable=False)

        class Meta:
            abstract = True

    class TaggedAudit(AuditFields):
        tag = StringField(default="general")

        class Meta:
            abstract = True

    class AuditRecord(TaggedAudit):
        score = IntegerField(default=0)

    assert [field.require_name() for field in AuditFields._meta.get_fields()] == ["created_by"]
    assert [field.require_name() for field in AuditRecord._meta.get_fields()] == [
        "id",
        "created_by",
        "tag",
        "score",
    ]
    record = AuditRecord(created_by="agent")
    assert record.tag == "general"
    assert record.score == 0


def test_inherited_fields_are_isolated_between_siblings():
    class Labelled(Model):
        label = StringField(max_length=40)

        class Meta:
            abstract = True

    class AlphaLabel(Labelled):
        pass

    class BetaLabel(Labelled):
        pass

    base_field = Labelled._meta.get_field("label")
    alpha_field = AlphaLabel._meta.get_field("label")
    beta_field = BetaLabel._meta.get_field("label")
    assert base_field is not alpha_field
    assert alpha_field is not beta_field
    assert alpha_field.require_model() is AlphaLabel
    assert beta_field.require_model() is BetaLabel
    alpha_field.db_column = "alpha_label"
    assert beta_field.db_column == "label"


def test_subclass_override_keeps_inherited_position():
    class Named(Model):
        name = StringField(max_length=100)
        rank = IntegerField()

        class Meta:
            abstract = True

    class ShortName(Named):
        name = StringField(max_length=12)

    assert [field.require_name() for field in ShortName._meta.get_fields()] == [
        "id",
        "name",
        "rank",
    ]
    assert ShortName._meta.get_field("name").max_length == 12


def test_multiple_abstract_base_conflict_requires_override():
    class LeftCode(Model):
        code = StringField()

        class Meta:
            abstract = True

    class RightCode(Model):
        code = IntegerField()

        class Meta:
            abstract = True

    with pytest.raises(ModelConfigurationError, match="code"):

        class AmbiguousCode(LeftCode, RightCode):
            pass

    class ResolvedCode(LeftCode, RightCode):
        code = StringField(max_length=8)

    assert ResolvedCode._meta.get_field("code").max_length == 8


def test_abstract_primary_key_is_cloned_without_auto_id():
    class ExternalIdentity(Model):
        key = StringField(primary_key=True, nullable=False)

        class Meta:
            abstract = True

    class ExternalRecord(ExternalIdentity):
        value = StringField()

    assert ExternalIdentity._meta.primary_key.require_name() == "key"
    assert ExternalRecord._meta.primary_key.require_name() == "key"
    assert [field.require_name() for field in ExternalRecord._meta.get_fields()] == [
        "key",
        "value",
    ]
    assert ExternalRecord._meta.primary_key is not ExternalIdentity._meta.primary_key


def test_inherited_relationships_rebind_and_generate_schema():
    class AbstractRelationTarget(Model):
        name = StringField()

    class RelatedFields(Model):
        owner = ForeignKey(AbstractRelationTarget, related_name="owned_records")
        profile = OneToOneField(AbstractRelationTarget, related_name="profile_record")
        tags = ManyToManyField(
            AbstractRelationTarget,
            related_name="tagged_records",
            db_table="record_tags",
        )

        class Meta:
            abstract = True

    class RelationRecord(RelatedFields):
        title = StringField()

    owner = RelationRecord._meta.get_field("owner")
    profile = RelationRecord._meta.get_field("profile")
    tags = RelationRecord._meta.many_to_many[0]
    assert owner.require_model() is RelationRecord
    assert profile.require_model() is RelationRecord
    assert tags.require_model() is RelationRecord
    assert owner is not RelatedFields._meta.get_field("owner")
    assert tags is not RelatedFields._meta.many_to_many[0]
    assert tags.db_table == "record_tags"

    builder = SchemaBuilder(SQLiteDialect())
    table_sql = builder.create_table_sql(RelationRecord)
    m2m_sql = builder.create_many_to_many_sql(RelationRecord)
    assert 'FOREIGN KEY ("owner")' in table_sql
    assert 'FOREIGN KEY ("profile")' in table_sql
    assert any('CREATE TABLE IF NOT EXISTS "record_tags"' in sql for sql in m2m_sql)


def test_inherited_scalar_field_persists(tmp_path):
    class Described(Model):
        description = StringField(nullable=False)

        class Meta:
            abstract = True

    class StoredItem(Described):
        quantity = IntegerField(default=1)

    session = Session(
        SQLiteAdapter(),
        connection_config=ConnectionConfig(url=f"sqlite:///{tmp_path / 'abstract.db'}"),
    )
    session.execute(SchemaBuilder(SQLiteDialect()).create_table_sql(StoredItem))
    item = StoredItem(description="inherited")
    session.add(item)
    session.commit()

    loaded = session.query(StoredItem).get(id=item.id)
    assert loaded.description == "inherited"
    assert loaded.quantity == 1
