import pytest

from blazeorm.adapters import AdapterConfigurationError, ConnectionConfig


def test_from_dsn_parses_core_fields_and_options():
    config = ConnectionConfig.from_dsn(
        "postgresql://user:secret@localhost:5432/dbname?"
        "autocommit=true&timeout=2.5&isolation_level=serializable&"
        "connect_timeout=3&application_name=blaze"
    )
    assert config.autocommit is True
    assert config.timeout == 2.5
    assert config.isolation_level == "serializable"
    assert config.options is not None
    assert config.options["connect_timeout"] == 3
    assert config.options["application_name"] == "blaze"
    assert config.ssl is None


def test_from_dsn_parses_postgres_ssl_options():
    config = ConnectionConfig.from_dsn(
        "postgresql://user:secret@localhost:5432/dbname?"
        "sslmode=require&sslrootcert=/ca.pem&sslcert=/cert.pem&sslkey=/key.pem"
    )
    assert config.ssl is not None
    assert config.ssl.mode == "require"
    assert config.ssl.rootcert == "/ca.pem"
    assert config.ssl.cert == "/cert.pem"
    assert config.ssl.key == "/key.pem"


def test_from_dsn_parses_mysql_ssl_options():
    config = ConnectionConfig.from_dsn(
        "mysql://user:secret@localhost:3306/dbname?"
        "ssl_ca=/ca.pem&ssl_cert=/cert.pem&ssl_key=/key.pem&ssl_check_hostname=true"
    )
    assert config.ssl is not None
    assert config.ssl.ca == "/ca.pem"
    assert config.ssl.cert == "/cert.pem"
    assert config.ssl.key == "/key.pem"
    assert config.ssl.check_hostname is True


def test_from_dsn_options_override():
    config = ConnectionConfig.from_dsn(
        "postgresql://user:secret@localhost:5432/dbname?connect_timeout=3",
        options={"connect_timeout": 9},
    )
    assert config.options is not None
    assert config.options["connect_timeout"] == 9


def test_invalid_autocommit_value_raises():
    with pytest.raises(AdapterConfigurationError):
        ConnectionConfig.from_dsn("postgresql://user:secret@localhost:5432/dbname?autocommit=maybe")
