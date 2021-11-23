import flask
import pytest

from feedcloud import api, database, settings


@pytest.fixture(scope="session", autouse=True)
def configure_settings():
    settings.update_settings_from_dict(
        {"DATABASE_URL": "postgresql://test:test@localhost:5432/feedcloud"}
    )


@pytest.fixture()
def clean_db():
    database.drop_all()
    database.create_all()


@pytest.fixture()
def db_session(clean_db):
    session = database.get_session()
    yield session
    session.close()


@pytest.fixture
def app():
    return api.app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def push_request_context(request, app):
    ctx = app.test_request_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
