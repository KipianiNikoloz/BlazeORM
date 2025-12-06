Examples
========

What Lives Here
---------------
- `blog_app/`: Reference application showing models, migrations, seeding, and feed generation.
  - `models.py`: Blog domain models with relationships.
  - `demo.py`: Bootstrap helpers (`bootstrap_session`), seeding (`seed_sample_data`), `run_demo` to return a rendered feed, plus QuerySet-based feeds, author/post prefetch, and a small performance demo.
- `library_app/`: Secondary example highlighting many-to-many usage (books/genres) and select_related/prefetch_related patterns.
  - `models.py`: Library domain with writers, books, genres (m2m).
  - `demo.py`: Bootstrap, seed, and fetch books with authors/genres via eager loading.

How to Run
----------
```bash
python -m examples.blog_app.demo
# or
python -m examples.library_app.demo
```
or import `bootstrap_session` / `seed_sample_data` in your own scripts/tests.

Additional Tips
---------------
- The blog app `demo.py` includes `queryset_feed`, `author_with_posts`, and `performance_demo` to showcase eager loading and the PerformanceTracker.
- The library app demonstrates m2m mutation via `book.genres.add(...)` and eager loading combined with filters using `Q`.

Testing References
------------------
- `tests/examples/test_blog_app.py` ensures bootstrap/seed/demo flows succeed.
- `tests/examples/test_library_app.py` validates bootstrap/seed and eager-loading feed for the library example.
