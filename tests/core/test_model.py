import pytest

from blazeorm.core import (
    BooleanField,
    DateTimeField,
    IntegerField,
    Model,
    ModelConfigurationError,
    StringField,
)


class User(Model):
    name = StringField(max_length=50, nullable=False)
    age = IntegerField(default=0)
    is_active = BooleanField(default=True)


def test_model_metadata_collects_fields_in_order():
    assert list(User._meta.fields.keys()) == ["id", "name", "age", "is_active"]
    assert User._meta.primary_key.name == "id"
    assert User._meta.table_name == "user"


def test_model_initializes_defaults():
    user = User(name="Alice")
    assert user.name == "Alice"
    assert user.age == 0
    assert user.is_active is True
    assert user.pk is None


def test_setting_field_enforces_choices():
    class Article(Model):
        status = StringField(choices=("draft", "published"), default="draft")

    article = Article()
    with pytest.raises(ValueError):
        article.status = "archived"


def test_non_nullable_field_rejects_none():
    class Profile(Model):
        email = StringField(nullable=False)

    profile = Profile(email="user@example.com")
    assert profile.email == "user@example.com"

    with pytest.raises(ValueError):
        profile.email = None


def test_custom_primary_key_prevents_auto_field():
    class Token(Model):
        token_id = StringField(primary_key=True)

    assert list(Token._meta.fields.keys()) == ["token_id"]
    assert Token._meta.primary_key.name == "token_id"


def test_model_pk_property_returns_primary_key_value():
    class Post(Model):
        identifier = IntegerField(primary_key=True)
        title = StringField()

    post = Post(identifier=12, title="Hello")
    assert post.pk == 12


def test_auto_now_add_datetime_field():
    class Audit(Model):
        created_at = DateTimeField(auto_now_add=True, nullable=False)

    audit = Audit()
    assert audit.created_at is not None
    assert hasattr(audit.created_at, "isoformat")


def test_duplicate_primary_key_raises_error():
    with pytest.raises(ModelConfigurationError):

        class BadModel(Model):
            code = IntegerField(primary_key=True)
            other = IntegerField(primary_key=True)


def test_manual_id_field_without_primary_key_errors():
    with pytest.raises(ModelConfigurationError):

        class BadIdentifier(Model):
            id = IntegerField()
