"""
Library example showcasing many-to-many and eager loading.
"""

from __future__ import annotations

from typing import Any, Dict, List

from blazeorm.adapters import SQLiteAdapter
from blazeorm.dialects import SQLiteDialect
from blazeorm.persistence import Session
from blazeorm.persistence.session import _current_session
from blazeorm.query import Q
from blazeorm.schema import MigrationEngine, MigrationOperation, SchemaBuilder

from .models import Book, Genre, Writer

APP_LABEL = "library_example"
MIGRATION_NAME = "0001_initial"


def bootstrap_session(dsn: str = "sqlite:///:memory:") -> Session:
    adapter = SQLiteAdapter()
    session = Session(adapter, dsn=dsn)
    _ensure_schema(session)
    return session


def _ensure_schema(session: Session) -> None:
    engine = MigrationEngine(session.adapter, session.dialect)
    applied = set(engine.applied_migrations())
    if (APP_LABEL, MIGRATION_NAME) in applied:
        return
    builder = SchemaBuilder(SQLiteDialect())
    ops: List[MigrationOperation] = []
    for model in (Writer, Genre, Book):
        ops.append(MigrationOperation(sql=builder.create_table_sql(model)))
    ops += [MigrationOperation(sql=stmt) for stmt in builder.create_many_to_many_sql(Book)]
    engine.apply(APP_LABEL, MIGRATION_NAME, ops)


def seed_sample_data(session: Session) -> Dict[str, List[Dict[str, Any]]]:
    writers = [
        Writer(name="Octavia Butler", country="USA"),
        Writer(name="Haruki Murakami", country="Japan"),
    ]
    genres = [
        Genre(name="Sci-Fi"),
        Genre(name="Magical Realism"),
        Genre(name="Fantasy"),
    ]
    token = _current_session.set(session)
    try:
        with session.transaction():
            for w in writers:
                session.add(w)
            for g in genres:
                session.add(g)
            session.flush()
            books = [
                Book(title="Kindred", published=True, author=writers[0]),
                Book(title="Kafka on the Shore", published=True, author=writers[1]),
            ]
            for book in books:
                session.add(book)
            session.flush()
            session.add_m2m(books[0], "genres", genres[0])
            session.add_m2m(books[1], "genres", genres[1], genres[2])
    finally:
        _current_session.reset(token)

    return {
        "writers": [w.to_dict() for w in writers],
        "genres": [g.to_dict() for g in genres],
        "books": [b.to_dict() for b in books],
    }


def fetch_books_with_authors(session: Session) -> List[Dict[str, Any]]:
    books = (
        session.query(Book)
        .select_related("author")
        .prefetch_related("genres")
        .where(Q(published=True))
    )
    result: List[Dict[str, Any]] = []
    for book in books:
        result.append(
            {
                "title": book.title,
                "author": book.author.name if book.author else None,
                "genres": [g.name for g in book.genres],
            }
        )
    return result


def run_demo(dsn: str = "sqlite:///:memory:") -> List[Dict[str, Any]]:
    session = bootstrap_session(dsn)
    try:
        seed_sample_data(session)
        return fetch_books_with_authors(session)
    finally:
        session.close()


if __name__ == "__main__":
    feed = run_demo("sqlite:///library_demo.db")
    for entry in feed:
        print(f"{entry['title']} by {entry['author']} [{', '.join(entry['genres'])}]")
