"""
Field definitions and descriptors for BlazeORM models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, Sequence, cast

if TYPE_CHECKING:
    from .model import Model


class FieldError(Exception):
    """Internal exception for field configuration issues."""


class Field:
    """
    Base class for model field descriptors.

    Fields manage attribute storage on model instances and retain metadata
    required for schema generation and validation.
    """

    _creation_counter = 0

    def __init__(
        self,
        *,
        primary_key: bool = False,
        unique: bool = False,
        nullable: bool = True,
        default: Any = None,
        db_type: Optional[str] = None,
        db_column: Optional[str] = None,
        db_default: Any = None,
        index: bool = False,
        choices: Optional[Sequence[Any]] = None,
        validators: Optional[Iterable[Callable[[Any], None]]] = None,
        help_text: Optional[str] = None,
    ) -> None:
        self.primary_key = primary_key
        self.unique = unique
        self.nullable = nullable
        self.default = default
        self.db_type = db_type
        self.db_column = db_column
        self.db_default = db_default
        self.index = index
        self.choices = tuple(choices) if choices is not None else None
        self.validators = list(validators or [])
        self.help_text = help_text

        self.model: type["Model"] | None = None  # Will be set during contribute_to_class
        self.name: str | None = None
        self.creation_counter = Field._creation_counter
        Field._creation_counter += 1

    # Descriptor protocol -------------------------------------------------
    def __get__(self, instance: object | None, owner: type | None = None) -> Any:
        if instance is None:
            return self

        model_instance = cast("Model", instance)
        name = self.require_name()
        value = model_instance._field_values.get(name)
        if value is None and name not in model_instance._field_values:
            default = self.get_default()
            if default is not None or self.default is not None:
                model_instance._field_values[name] = default
                return default
        return value

    def __set__(self, instance: object, value: Any) -> None:
        model_instance = cast("Model", instance)
        name = self.require_name()
        if value is None:
            if not self.nullable and not self.primary_key:
                raise ValueError(f"Field '{name}' cannot be None")
            model_instance._field_values[name] = None
            return

        if self.choices and value not in self.choices:
            raise ValueError(f"Value '{value}' for field '{name}' not in choices {self.choices}")

        python_value = self.to_python(value)
        model_instance._field_values[name] = python_value

    # Metadata helpers ----------------------------------------------------
    def bind(self, model: type["Model"], name: str) -> None:
        self.model = model
        self.name = name
        if self.db_column is None:
            self.db_column = name

    def contribute_to_class(self, model: type["Model"], name: str) -> None:
        """
        Attach the field to the model class as a descriptor.
        """
        self.bind(model, name)
        setattr(model, name, self)

    def require_name(self) -> str:
        if self.name is None:
            raise FieldError("Field name is not set.")
        return self.name

    def require_model(self) -> type["Model"]:
        if self.model is None:
            raise FieldError("Field model is not set.")
        return self.model

    def column_name(self) -> str:
        if self.db_column:
            return self.db_column
        return self.require_name()

    # Conversion / validation ---------------------------------------------
    def get_default(self) -> Any:
        if callable(self.default):
            return self.default()
        return self.default

    def to_python(self, value: Any) -> Any:
        return value

    def run_validators(self, value: Any) -> None:
        for validator in self.validators:
            validator(value)

    # Utilities -----------------------------------------------------------
    def clone(self) -> "Field":
        """
        Create a shallow copy of this field. Subclasses should override if
        they accept additional initialization arguments.
        """
        params = {
            "primary_key": self.primary_key,
            "unique": self.unique,
            "nullable": self.nullable,
            "default": self.default,
            "db_type": self.db_type,
            "db_column": self.db_column,
            "db_default": self.db_default,
            "index": self.index,
            "choices": self.choices,
            "validators": list(self.validators),
            "help_text": self.help_text,
        }
        cloned = self.__class__(**params)  # type: ignore[arg-type,call-arg]
        return cloned

    @property
    def has_default(self) -> bool:
        return self.default is not None or callable(self.default)

    def deconstruct(self) -> dict[str, Any]:
        """
        Provide a serializable representation used by migrations. For now,
        returns a minimal mapping.
        """
        name = self.require_name()
        return {
            "name": name,
            "primary_key": self.primary_key,
            "unique": self.unique,
            "nullable": self.nullable,
            "default": self.default,
            "db_type": self.db_type,
            "db_column": self.db_column,
            "db_default": self.db_default,
            "index": self.index,
            "choices": self.choices,
        }


class AutoField(Field):
    """
    Auto-incrementing integer field used as default primary key.
    """

    def __init__(self) -> None:
        super().__init__(primary_key=True, nullable=False, db_type="INTEGER")

    def to_python(self, value: Any) -> int | None:
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid value '{value}' for AutoField") from exc


class IntegerField(Field):
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("db_type", "INTEGER")
        super().__init__(**kwargs)

    def to_python(self, value: Any) -> int | None:
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid integer value '{value}'") from exc


class FloatField(Field):
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("db_type", "REAL")
        super().__init__(**kwargs)

    def to_python(self, value: Any) -> float | None:
        if value is None:
            return value
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid float value '{value}'") from exc


class BooleanField(Field):
    def __init__(self, *, default: Any = False, **kwargs: Any) -> None:
        kwargs.setdefault("db_type", "BOOLEAN")
        kwargs.setdefault("nullable", False)
        super().__init__(default=default, **kwargs)

    def to_python(self, value: Any) -> bool | None:
        if value is None:
            return value
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in {"true", "t", "1"}:
                return True
            if lowered in {"false", "f", "0"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        raise ValueError(f"Invalid boolean value '{value}'")


class StringField(Field):
    def __init__(self, *, max_length: int = 255, **kwargs: Any) -> None:
        kwargs.setdefault("db_type", "TEXT")
        super().__init__(**kwargs)
        self.max_length = max_length

    def to_python(self, value: Any) -> str | None:
        if value is None:
            return value
        result = str(value)
        if self.max_length and len(result) > self.max_length:
            field_name = self.require_name()
            raise ValueError(f"Value for field '{field_name}' exceeds max_length {self.max_length}")
        return result

    def clone(self) -> "StringField":
        cloned = self.__class__(
            max_length=self.max_length,
            primary_key=self.primary_key,
            unique=self.unique,
            nullable=self.nullable,
            default=self.default,
            db_type=self.db_type,
            db_column=self.db_column,
            db_default=self.db_default,
            index=self.index,
            choices=self.choices,
            validators=list(self.validators),
            help_text=self.help_text,
        )
        return cloned


class DateTimeField(Field):
    def __init__(
        self, *, auto_now: bool = False, auto_now_add: bool = False, **kwargs: Any
    ) -> None:
        kwargs.setdefault("db_type", "TEXT")
        super().__init__(**kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def get_default(self) -> Any:
        if self.auto_now or self.auto_now_add:
            return datetime.now(timezone.utc)
        return super().get_default()

    def to_python(self, value: Any) -> datetime | None:
        if value is None:
            return value
        if isinstance(value, datetime):
            return value
        raise ValueError(f"Expected datetime for field '{self.name}', received {value!r}")

    def clone(self) -> "DateTimeField":
        cloned = self.__class__(
            auto_now=self.auto_now,
            auto_now_add=self.auto_now_add,
            primary_key=self.primary_key,
            unique=self.unique,
            nullable=self.nullable,
            default=self.default,
            db_type=self.db_type,
            db_column=self.db_column,
            db_default=self.db_default,
            index=self.index,
            choices=self.choices,
            validators=list(self.validators),
            help_text=self.help_text,
        )
        return cloned
