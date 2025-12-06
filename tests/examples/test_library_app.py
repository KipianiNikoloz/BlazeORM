from examples.library_app import (
    bootstrap_session,
    fetch_books_with_authors,
    run_demo,
    seed_sample_data,
)


def test_library_example_bootstrap_and_seed(tmp_path):
    db_path = tmp_path / "library_example.db"
    session = bootstrap_session(dsn=f"sqlite:///{db_path}")
    try:
        seeded = seed_sample_data(session)
        assert len(seeded["writers"]) == 2
        assert len(seeded["genres"]) == 3
        assert len(seeded["books"]) == 2

        books = fetch_books_with_authors(session)
        assert len(books) == 2
        assert {"title", "author", "genres"} <= books[0].keys()
        assert books[0]["genres"]
    finally:
        session.close()


def test_run_library_demo_returns_feed():
    feed = run_demo()
    assert feed
    assert all(entry["genres"] for entry in feed)
