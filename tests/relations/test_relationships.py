from blazeorm.core import ForeignKey, ManyToManyField, Model, StringField


class Author(Model):
    name = StringField(nullable=False)


class Article(Model):
    title = StringField(nullable=False)
    author = ForeignKey(Author, related_name="articles")


class Tag(Model):
    name = StringField()


class TaggedArticle(Model):
    title = StringField()
    owner = ForeignKey("Author")  # string reference resolution
    tags = ManyToManyField(Tag, related_name="tagged_articles")


class Comment(Model):
    body = StringField()
    post = ForeignKey("BlogPost", related_name="comments")


class BlogPost(Model):
    title = StringField()


def test_foreign_key_metadata_and_reverse_manager():
    field = Article._meta.get_field("author")
    assert field.remote_model is Author
    author = Author(id=5, name="Alice")
    manager = author.articles
    qs = manager.all()
    sql, params = qs.to_sql()
    assert 'WHERE "author" = ?' in sql
    assert params == [5]


def test_string_reference_resolved_and_default_related_name():
    field = TaggedArticle._meta.get_field("owner")
    assert field.remote_model is Author
    assert hasattr(Author, "taggedarticle_set")
    accessor = Author.taggedarticle_set
    assert accessor.field is field


def test_many_to_many_registered_in_meta():
    assert len(TaggedArticle._meta.many_to_many) == 1
    m2m_field = TaggedArticle._meta.many_to_many[0]
    assert isinstance(m2m_field, ManyToManyField)
    assert m2m_field.remote_model is Tag


def test_deferred_model_resolution():
    field = Comment._meta.get_field("post")
    assert field.remote_model is BlogPost
    assert hasattr(BlogPost, "comments")
