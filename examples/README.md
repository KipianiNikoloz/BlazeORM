Examples
========

What Lives Here
---------------
- `blog_app/`: Reference application showing models, migrations, seeding, and feed generation.
  - `models.py`: Blog domain models with relationships.
  - `demo.py`: Bootstrap helpers (`bootstrap_session`), seeding (`seed_sample_data`), and `run_demo` to return a rendered feed.

How to Run
----------
```bash
python -m examples.blog_app.demo
```
or import `bootstrap_session` / `seed_sample_data` in your own scripts/tests.

Testing References
------------------
- `tests/examples/test_blog_app.py` ensures bootstrap/seed/demo flows succeed.

