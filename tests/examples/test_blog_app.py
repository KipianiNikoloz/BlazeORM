from examples.blog_app import bootstrap_session, fetch_recent_posts, run_demo, seed_sample_data


def test_blog_example_bootstrap_and_seed(tmp_path):
    db_path = tmp_path / "blog_example.db"
    session = bootstrap_session(dsn=f"sqlite:///{db_path}")
    try:
        seeded = seed_sample_data(session)
        assert len(seeded["authors"]) == 2
        assert len(seeded["categories"]) == 2
        assert len(seeded["posts"]) == 2

        feed = fetch_recent_posts(session, limit=5)
        assert len(feed) == 2
        assert {"title", "author_name", "category_name"} <= feed[0].keys()
    finally:
        session.close()


def test_run_demo_returns_feed():
    feed = run_demo()
    assert feed
    assert all(entry["published"] for entry in feed)
