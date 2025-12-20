"""
Validation pipeline hooks used by models and sessions.
"""

from __future__ import annotations

from typing import Dict, List

from ..core.fields import AutoField, Field
from ..core.model import Model
from .errors import ValidationError


def validate_instance(instance: Model) -> None:
    errors: Dict[str, List[str]] = {}

    for field in instance._meta.get_fields():
        field_name = field.require_name()
        value = getattr(instance, field_name, None)
        try:
            _validate_field(field, value, instance)
        except ValidationError as exc:
            _merge_errors(errors, exc.errors)
        except Exception as exc:
            _add_error(errors, field_name, str(exc))

    # Model-level clean hook
    clean_method = getattr(instance, "clean", None)
    if callable(clean_method):
        try:
            clean_method()
        except ValidationError as exc:
            _merge_errors(errors, exc.errors)
        except Exception as exc:
            _add_error(errors, "__all__", str(exc))

    if errors:
        raise ValidationError(errors)


def _validate_field(field: Field, value, instance: Model) -> None:
    if value is None:
        if field.primary_key and isinstance(field, AutoField):
            return
        if not field.nullable:
            field_name = field.require_name()
            raise ValidationError({field_name: ["This field cannot be null."]})
        return

    try:
        field.run_validators(value)
    except Exception as exc:
        field_name = field.require_name()
        raise ValidationError({field_name: [str(exc)]}) from exc


def _add_error(errors: Dict[str, List[str]], field: str, message: str) -> None:
    errors.setdefault(field, []).append(message)


def _merge_errors(target: Dict[str, List[str]], source: Dict[str, List[str]]) -> None:
    for field, messages in source.items():
        target.setdefault(field, []).extend(messages)
