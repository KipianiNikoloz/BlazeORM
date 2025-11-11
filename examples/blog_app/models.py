"""
Data models for the BlazeORM blog example.
"""

from __future__ import annotations

from blazeorm.core import BooleanField, ForeignKey, Model, StringField


class Author(Model):
    name = StringField(nullable=False, max_length=120)
    email = StringField(nullable=False, unique=True, max_length=255)
    bio = StringField(default="", nullable=True)


class Category(Model):
    name = StringField(nullable=False, unique=True, max_length=80)
    description = StringField(default="", nullable=True)


class Post(Model):
    title = StringField(nullable=False, max_length=200)
    body = StringField(nullable=False)
    published = BooleanField(default=False)
    author = ForeignKey(Author, related_name="posts", db_column="author_id")
    category = ForeignKey(Category, related_name="posts", db_column="category_id")
