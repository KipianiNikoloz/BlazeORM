"""
Model base classes and metadata orchestration for BlazeORM.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, Optional, Type, TypeVar

from ..utils import camel_to_snake
from .fields import AutoField, Field
from .relations import ManyToManyField, RelatedField, relation_registry
from ..query.queryset import QueryManager


class ModelConfigurationError(Exception):
    """Raised when a model class is misconfigured."""


@dataclass
class ModelOptions:
    """
    Container for model metadata calculated by :class:`ModelMeta`.
    """

    model: Type["Model"]
    table_name: str = ""
    schema: Optional[str] = None
    abstract: bool = False
    fields: "OrderedDict[str, Field]" = field(default_factory=OrderedDict)
    primary_key: Optional[Field] = None
    many_to_many: list[ManyToManyField] = field(default_factory=list)
    m2m_through_tables: dict[str, str] = field(default_factory=dict)

    def add_field(self, field_obj: Field) -> None:
        if field_obj.name in self.fields:
            raise ModelConfigurationError(
                f"Duplicate field name '{field_obj.name}' on model '{self.model.__name__}'"
            )
        self.fields[field_obj.name] = field_obj
        if field_obj.primary_key:
            if self.primary_key and self.primary_key is not field_obj:
                raise ModelConfigurationError(
                    f"Multiple primary keys defined on model '{self.model.__name__}'"
                )
            self.primary_key = field_obj

    @property
    def table(self) -> str:
        if self.schema:
            return f"{self.schema}.{self.table_name}"
        return self.table_name

    def get_field(self, name: str) -> Field:
        try:
            return self.fields[name]
        except KeyError as exc:
            raise KeyError(f"Unknown field '{name}' on model '{self.model.__name__}'") from exc

    def get_fields(self) -> Iterable[Field]:
        return self.fields.values()


TModel = TypeVar("TModel", bound="Model")


class ModelMeta(type):
    """
    Metaclass responsible for collecting fields and establishing metadata.
    """

    def __new__(mcls, name: str, bases: tuple[type, ...], attrs: Dict[str, Any]) -> "ModelMeta":
        # Allow creation of the base Model class without processing fields.
        if name == "Model" and bases == (object,):
            return super().__new__(mcls, name, bases, attrs)

        declared_fields: Dict[str, Field] = {}
        for attr_name, value in list(attrs.items()):
            if isinstance(value, Field):
                declared_fields[attr_name] = attrs.pop(attr_name)

        cls = super().__new__(mcls, name, bases, attrs)

        meta = getattr(cls, "Meta", None)
        table_name = camel_to_snake(name)
        schema = None
        abstract = False

        if meta:
            table_name = getattr(meta, "table", table_name)
            schema = getattr(meta, "schema", None)
            abstract = getattr(meta, "abstract", False)

        cls._meta = ModelOptions(model=cls, table_name=table_name, schema=schema, abstract=abstract)

        # TODO: Support inheriting fields from abstract base models.
        sorted_fields = sorted(
            declared_fields.items(), key=lambda item: item[1].creation_counter
        )
        for attr_name, field_obj in sorted_fields:
            field_obj.contribute_to_class(cls, attr_name)
            if isinstance(field_obj, ManyToManyField):
                field_obj.model = cls
                relation_registry.register_field(cls, field_obj)
                continue
            cls._meta.add_field(field_obj)
            if isinstance(field_obj, RelatedField):
                relation_registry.register_field(cls, field_obj)

        if not cls._meta.primary_key and not cls._meta.abstract:
            if "id" in cls._meta.fields:
                raise ModelConfigurationError(
                    f"Model '{cls.__name__}' defines a field named 'id' but no primary key. "
                    "Either set primary_key=True on that field or define a different name."
                )
            auto_field = AutoField()
            auto_field.contribute_to_class(cls, "id")
            cls._meta.add_field(auto_field)
            cls._meta.fields = OrderedDict(
                sorted(
                    cls._meta.fields.items(),
                    key=lambda item: (0 if item[0] == "id" else 1, item[1].creation_counter),
                )
            )

        if "objects" not in cls.__dict__:
            cls.objects = QueryManager(cls)

        relation_registry.register_model(cls)

        return cls


class Model(metaclass=ModelMeta):
    """
    Base model providing data container functionality.
    Persistence operations are supplied by the persistence layer.
    """

    def __init__(self, **kwargs: Any) -> None:
        self._field_values: Dict[str, Any] = {}
        self._initial_state: Dict[str, Any] = {}
        self._related_cache: Dict[str, Any] = {}

        for field in self._meta.get_fields():
            if field.primary_key and field.has_default is False and field.name not in kwargs:
                # Primary key may be assigned by database later.
                continue

            if field.name in kwargs:
                setattr(self, field.name, kwargs[field.name])
            elif field.has_default:
                default_value = field.get_default()
                if default_value is not None:
                    setattr(self, field.name, default_value)

        # Retain snapshot for simple dirty tracking
        self._initial_state = dict(self._field_values)

    def __repr__(self) -> str:
        field_parts = ", ".join(
            f"{field.name}={repr(self._field_values.get(field.name))}"
            for field in self._meta.get_fields()
            if field.name in self._field_values
        )
        return f"<{self.__class__.__name__} {field_parts}>"

    @property
    def pk(self) -> Any:
        if not self._meta.primary_key:
            raise ModelConfigurationError(
                f"Model '{self.__class__.__name__}' does not define a primary key."
            )
        return getattr(self, self._meta.primary_key.name)

    def to_dict(self) -> Dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in self._meta.get_fields()}

    def is_dirty(self) -> bool:
        return any(
            self._field_values.get(name) != self._initial_state.get(name)
            for name in self._field_values
        )

    # Placeholder persistence hooks --------------------------------------
    def save(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Persistence layer must implement 'save'.")

    def delete(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Persistence layer must implement 'delete'.")

    # Validation --------------------------------------------------------
    def full_clean(self) -> None:
        from ..validation import validate_instance

        validate_instance(self)

    def clean(self) -> None:
        """
        Hook for subclasses to implement model-level validation.
        """
        return None

    @classmethod
    def register_hook(cls, event: str, handler) -> None:
        from ..hooks import hooks

        hooks.register(event, handler, model=cls)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..hooks import HookDispatcher
