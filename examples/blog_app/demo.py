"""
Utility helpers for running the BlazeORM blog example end-to-end.
"""

from __future__ import annotations

from typing import Any, Dict, List

from blazeorm.adapters import SQLiteAdapter
from blazeorm.dialects import Dialect, SQLiteDialect
from blazeorm.persistence import Session
from blazeorm.query import Q
from blazeorm.schema import MigrationEngine, MigrationOperation, SchemaBuilder

from .models import Author, Category, Post

APP_LABEL = "blog_example"
MIGRATION_NAME = "0001_initial"


def bootstrap_session(dsn: str = "sqlite:///:memory:") -> Session:
    """
    Create a SQLite-backed session and ensure the blog schema exists.
    """

    adapter = SQLiteAdapter()
    session = Session(adapter, dsn=dsn)
    _ensure_schema(session)
    return session


def seed_sample_data(session: Session) -> Dict[str, List[Dict[str, Any]]]:
    """
    Populate authors, categories, and posts to make the example interactive.
    """

    authors = [
        Author(name="Alice Carter", email="alice@example.com", bio="Editor-in-chief."),
        Author(name="Brian Kim", email="brian@example.com", bio="Performance specialist."),
    ]
    categories = [
        Category(name="Announcements", description="Release notes and launch news."),
        Category(name="Guides", description="Deep dives and tutorials."),
    ]

    with session.transaction():
        for author in authors:
            session.add(author)
        for category in categories:
            session.add(category)
        # Persist authors/categories so we can reference their IDs for posts.
        session.flush()
        posts = [
            Post(
                title="Introducing BlazeORM",
                body="This guide walks through setting up sessions, models, and migrations.",
                published=True,
                author=authors[0],
                category=categories[0],
            ),
            Post(
                title="Eliminating N+1 Queries",
                body="Use select_related and caching layers to tame N+1 problems.",
                published=True,
                author=authors[1],
                category=categories[1],
            ),
        ]
        for post in posts:
            session.add(post)

    return {
        "authors": [author.to_dict() for author in authors],
        "categories": [category.to_dict() for category in categories],
        "posts": [post.to_dict() for post in posts],
    }


def fetch_recent_posts(session: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve a feed of published posts with author and category metadata.
    """

    sql = """
    SELECT
        p.id,
        p.title,
        p.published,
        a.name AS author_name,
        c.name AS category_name
    FROM "post" AS p
    JOIN "author" AS a ON p.author_id = a.id
    JOIN "category" AS c ON p.category_id = c.id
    WHERE p.published = 1
    ORDER BY p.id DESC
    LIMIT ?
    """
    rows = session.execute(sql, (limit,)).fetchall()
    return [dict(row) for row in rows]


def queryset_feed(session: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Return published posts using QuerySet APIs with select_related for joins.
    Demonstrates LINQ-like chaining and eager loading.
    """

    posts = (
        session.query(Post)
        .select_related("author", "category")
        .where(Q(published=True))
        .order_by("-id")
        .limit(limit)
    )
    feed: List[Dict[str, Any]] = []
    for post in posts:
        feed.append(
            {
                "id": post.id,
                "title": post.title,
                "published": post.published,
                "author_name": post.author.name if post.author else None,
                "category_name": post.category.name if post.category else None,
            }
        )
    return feed


def author_with_posts(session: Session) -> List[Dict[str, Any]]:
    """
    Prefetch posts per author to avoid N+1 queries.
    """

    authors = session.query(Author).prefetch_related("posts").order_by("id")
    result: List[Dict[str, Any]] = []
    for author in authors:
        result.append(
            {
                "author": author.name,
                "posts": [p.title for p in author.posts],
            }
        )
    return result


def performance_demo(session: Session, threshold: int = 2) -> Dict[str, Any]:
    """
    Illustrate PerformanceTracker usage by running a small N+1 pattern
    followed by an optimized prefetch.
    """

    session.performance.reset()
    # Deliberate N+1
    for post in session.query(Post).order_by("id"):
        _ = post.author  # triggers FK access per row if not eager loaded
    n_plus_one_stats = session.query_stats()

    session.performance.reset()
    # Optimized with eager loading
    for post in session.query(Post).select_related("author"):
        _ = post.author
    optimized_stats = session.query_stats()

    return {
        "n_plus_one": n_plus_one_stats,
        "optimized": optimized_stats,
        "threshold": threshold,
    }


def run_demo(dsn: str = "sqlite:///:memory:") -> List[Dict[str, Any]]:
    """
    Bootstrap the database, seed data, and return a rendered feed.
    """

    session = bootstrap_session(dsn=dsn)
    try:
        seed_sample_data(session)
        return fetch_recent_posts(session)
    finally:
        session.close()


def _ensure_schema(session: Session) -> None:
    engine = MigrationEngine(session.adapter, session.dialect)
    applied = set(engine.applied_migrations())
    if (APP_LABEL, MIGRATION_NAME) in applied:
        return
    operations = _initial_operations(session.dialect)
    engine.apply(APP_LABEL, MIGRATION_NAME, operations)


def _initial_operations(dialect: Dialect | None = None) -> List[MigrationOperation]:
    builder = SchemaBuilder(dialect or SQLiteDialect())
    operations: List[MigrationOperation] = []
    for model in (Author, Category, Post):
        sql = builder.create_table_sql(model)
        operations.append(
            MigrationOperation(
                sql=sql,
                description=f"create {model.__name__.lower()} table",
            )
        )
    return operations


if __name__ == "__main__":
    feed = run_demo("sqlite:///blog_demo.db")
    for entry in feed:
        print(f"[{entry['category_name']}] {entry['title']} by {entry['author_name']}")
