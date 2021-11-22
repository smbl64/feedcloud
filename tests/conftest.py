import pytest

from feedcloud import database


@pytest.fixture(scope="session", autouse=True)
def configure_settings():
    pass


@pytest.fixture()
def clean_db():
    database.drop_all()
    database.create_all()


@pytest.fixture()
def db_session(clean_db):
    session = database.get_session()
    yield session
    session.close()
