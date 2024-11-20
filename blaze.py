import sqlite3


class Field:
    """Defines a database field with a name and type."""
    def __init__(self, field_type):
        self.field_type = field_type
        self.name = None  # Will be set by Model metaclass


class IntegerField(Field):
    def __init__(self):
        super().__init__("INTEGER")


class FloatField(Field):
    def __init__(self):
        super().__init__("FLOAT")


class StringField(Field):
    def __init__(self, max_length=255):
        super().__init__(f"TEXT({max_length})")


class ModelMeta(type):
    """Metaclass for Model to handle table and field mappings."""
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return super().__new__(cls, name, bases, attrs)

        table_name = name.lower()
        fields = {}

        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                value.name = key
                fields[key] = value
                del attrs[key]

        attrs['_table'] = table_name
        attrs['_fields'] = fields

        return super().__new__(cls, name, bases, attrs)


class Model(metaclass=ModelMeta):
    """Base model class that includes CRUD operations."""
    def __init__(self, **kwargs):
        for field_name in self._fields:
            setattr(self, field_name, kwargs.get(field_name))

    @classmethod
    def connect(cls, db_name="database.db"):
        cls._connection = sqlite3.connect(db_name)
        cls._connection.row_factory = sqlite3.Row
        cls._cursor = cls._connection.cursor()

    @classmethod
    def create_table(cls):
        fields = [
            f"{name} {field.field_type}" for name, field in cls._fields.items()
        ]
        sql = f"CREATE TABLE IF NOT EXISTS {cls._table} (id INTEGER PRIMARY KEY, {', '.join(fields)})"
        cls._cursor.execute(sql)
        cls._connection.commit()

    def save(self):
        fields = ', '.join(self._fields.keys())
        placeholders = ', '.join('?' for _ in self._fields)
        values = tuple(getattr(self, field) for field in self._fields)
        sql = f"INSERT INTO {self._table} ({fields}) VALUES ({placeholders})"
        self._cursor.execute(sql, values)
        self._connection.commit()
        self.id = self._cursor.lastrowid  # Save the id of the inserted row

    @classmethod
    def get(cls, **kwargs):
        key, value = list(kwargs.items())[0]
        sql = f"SELECT * FROM {cls._table} WHERE {key} = ?"
        cls._cursor.execute(sql, (value,))
        row = cls._cursor.fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def all(cls):
        sql = f"SELECT * FROM {cls._table}"
        cls._cursor.execute(sql)
        rows = cls._cursor.fetchall()
        return [cls(**dict(row)) for row in rows]

    def delete(self):
        sql = f"DELETE FROM {self._table} WHERE id = ?"
        self._cursor.execute(sql, (self.id,))
        self._connection.commit()

    @classmethod
    def close_connection(cls):
        cls._connection.close()

