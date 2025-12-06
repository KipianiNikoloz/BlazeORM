"""
Data models for the BlazeORM library example.
"""

from __future__ import annotations

from blazeorm.core import BooleanField, ForeignKey, ManyToManyField, Model, StringField


class Writer(Model):
    name = StringField(nullable=False, max_length=120)
    country = StringField(nullable=True)


class Genre(Model):
    name = StringField(nullable=False, unique=True, max_length=80)


class Book(Model):
    title = StringField(nullable=False, max_length=200)
    published = BooleanField(default=False)
    author = ForeignKey(Writer, related_name="books", db_column="author_id")
    genres = ManyToManyField(Genre, related_name="books")
