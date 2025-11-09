import pytest

from blazeorm.core import IntegerField, Model, StringField
from blazeorm.validation import RegexValidator, ValidationError


class Profile(Model):
    username = StringField(nullable=False, validators=[RegexValidator(r"^[a-z0-9_]+$")])
    age = IntegerField(default=18)


def test_field_validation_error():
    profile = Profile(username="Invalid-Name")
    with pytest.raises(ValidationError) as excinfo:
        profile.full_clean()
    assert "username" in excinfo.value.errors


def test_model_clean_hook():
    class Account(Model):
        email = StringField(nullable=False)
        confirm_email = StringField(nullable=False)

        def clean(self):
            if self.email != self.confirm_email:
                raise ValidationError({"email": ["Emails must match."]})

    account = Account(email="a@example.com", confirm_email="b@example.com")
    with pytest.raises(ValidationError) as excinfo:
        account.full_clean()
    assert excinfo.value.errors["email"] == ["Emails must match."]


def test_nullable_fields_pass():
    class Optional(Model):
        nickname = StringField(nullable=True)

    obj = Optional()
    obj.full_clean()  # should not raise
