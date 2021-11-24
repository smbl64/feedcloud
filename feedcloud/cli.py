import click

from feedcloud import constants, database, helpers
from feedcloud.ingest.worker import FeedWorker


@click.group()
def cli():
    pass


@cli.group("database")
def database_group():
    pass


@database_group.command("init")
@click.option("--delete-all", default=False, is_flag=True)
def init_database(delete_all):
    if delete_all:
        click.echo("Deleting all exisiting tables and data...")
        database.drop_all()

    click.echo("Creating tables...")
    database.create_all()

    click.echo("Done")


@cli.group("user")
def user_group():
    pass


@user_group.command()
def create_root():
    """
    Create the default root user.
    """
    create_user(
        constants.DEFAULT_ADMIN_USER, constants.DEFAULT_ADMIN_USER, is_admin=True
    )


@user_group.command("create")
@click.option("--username", "-u", required=True)
@click.password_option()
def create_normal_user(username: str, password: str) -> None:
    """
    Create a new user.
    """
    print(password)
    create_user(username, password, is_admin=False)


def create_user(username: str, password: str, *, is_admin: bool) -> None:
    User = database.User

    with database.get_session() as session:
        if session.query(User).filter(User.username == username).count() != 0:
            click.echo(f"User '{username}' already exists.")
            return

        user = User(
            username=username,
            password_hash=helpers.hash_password(password),
            is_admin=is_admin,
        )
        session.add(user)
        session.commit()


@cli.command()
def woot():
    url = "https://www.nu.nl/rss/Algemeen"
    url = "https://feeds.feedburner.com/tweakers/mixed"
    url = "http://bad-url.xyz:1234"
    # database.drop_all()
    # database.create_all()
    with database.get_session() as session:
        user = (
            session.query(database.User)
            .filter(database.User.username == "foo")
            .one_or_none()
        )
        if not user:
            user = database.User(username="foo", password_hash="bar")
            session.add(user)
            session.flush()

        feed = (
            session.query(database.Feed).filter(database.Feed.url == url).one_or_none()
        )
        if not feed:
            feed = database.Feed(url=url, user=user)
            session.add(feed)

        session.commit()

        session.refresh(feed)

    print(feed.url)
    worker = FeedWorker(feed)
    worker.start()
