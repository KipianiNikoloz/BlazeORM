from dataclasses import FrozenInstanceError

import pytest

from blazeorm import Index as RootIndex
from blazeorm import UniqueConstraint as RootUniqueConstraint
from blazeorm.core import (
    Index,
    IntegerField,
    Model,
    ModelConfigurationError,
    StringField,
    UniqueConstraint,
)


def test_constraint_metadata_is_public_immutable_and_ordered():
    constraint = UniqueConstraint(fields=("tenant", "slug"), name="uq_tenant_slug")
    index = Index(fields=["status", "created_at"])

    assert constraint.fields == ("tenant", "slug")
    assert constraint.name == "uq_tenant_slug"
    assert index.fields == ("status", "created_at")
    assert RootUniqueConstraint is UniqueConstraint
    assert RootIndex is Index
    with pytest.raises(FrozenInstanceError):
        constraint.name = "changed"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: UniqueConstraint(fields=()),
        lambda: Index(fields=("slug", "slug")),
        lambda: Index(fields=("",)),
        lambda: UniqueConstraint(fields=(1,)),
        lambda: Index(fields=("slug",), name=""),
    ],
)
def test_constraint_metadata_rejects_invalid_fields_and_names(factory):
    with pytest.raises(ValueError):
        factory()


def test_model_collects_local_and_abstract_constraint_metadata():
    inherited_constraint = UniqueConstraint(fields=("tenant", "slug"))
    inherited_index = Index(fields=("slug",))

    class Slugged(Model):
        tenant = IntegerField(nullable=False)
        slug = StringField(nullable=False)

        class Meta:
            abstract = True
            constraints = (inherited_constraint,)
            indexes = (inherited_index,)

    local_constraint = UniqueConstraint(fields=("tenant", "title"), name="uq_title")
    local_index = Index(fields=("title", "slug"), name="idx_title_slug")

    class Article(Slugged):
        title = StringField(nullable=False)

        class Meta:
            constraints = (local_constraint,)
            indexes = (local_index,)

    assert Article._meta.constraints == (inherited_constraint, local_constraint)
    assert Article._meta.indexes == (inherited_index, local_index)


@pytest.mark.parametrize("metadata_name", ["constraints", "indexes"])
def test_model_rejects_unknown_constraint_fields(metadata_name):
    metadata = (
        UniqueConstraint(fields=("missing",))
        if metadata_name == "constraints"
        else Index(fields=("missing",))
    )

    with pytest.raises(ModelConfigurationError, match="unknown scalar field 'missing'"):

        class Invalid(Model):
            name = StringField()

            class Meta:
                locals()[metadata_name] = (metadata,)


@pytest.mark.parametrize("metadata_name", ["constraints", "indexes"])
def test_model_rejects_duplicate_metadata_definitions_and_names(metadata_name):
    metadata_type = UniqueConstraint if metadata_name == "constraints" else Index
    first = metadata_type(fields=("name",), name="duplicate")
    repeated = metadata_type(fields=("name",), name="other")

    with pytest.raises(ModelConfigurationError, match="duplicate"):

        class Invalid(Model):
            name = StringField()

            class Meta:
                locals()[metadata_name] = (first, repeated)
