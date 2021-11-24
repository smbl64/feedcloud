import dramatiq
import pytest

from feedcloud import api, database, helpers, settings


@pytest.fixture(scope="session", autouse=True)
def configure_settings():
    settings.update_settings_from_dict(
        {
            "DATABASE_URL": "postgresql://test:test@localhost:5432/feedcloud",
            "IS_TESTING": True
        }
    )


@pytest.fixture()
def clean_db():
    database.drop_all()
    database.create_all()


@pytest.fixture()
def db_session(clean_db):
    """
    Create a SQLAlchemy database session.
    Session will be closed automatically when the test is done.
    """
    session = database.get_session()
    yield session
    session.close()


@pytest.fixture
def app():
    return api.app


@pytest.fixture
def client(app):
    """
    Create a Flask test client for calling endpoints.
    """
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def push_request_context(request, app):
    """
    Push a Flask app context to each test so functions like `url_for` become
    available.

    This fixture will be used automatically before each test case (`autouse=True`).
    """
    ctx = app.test_request_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)


@pytest.fixture
def test_user(db_session):
    username = "test"
    password = "test"
    user = database.User(
        username=username,
        password_hash=helpers.hash_password(password),
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    return user


@pytest.fixture()
def broker():
    broker = dramatiq.get_broker()
    broker.flush_all()
    return broker


@pytest.fixture()
def stub_worker(broker):
    worker = dramatiq.Worker(broker, worker_timeout=100)
    worker.start()
    yield worker
    worker.stop()
