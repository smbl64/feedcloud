import click

from feedcloud import constants, database, helpers
from feedcloud.worker import FeedWorker


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


@cli.command()
def create_admin_user():
    """
    Create the default admin user.
    """
    admin_password = constants.DEFAULT_ADMIN_USER

    User = database.User

    with database.get_session() as session:
        if session.query(User.username == constants.DEFAULT_ADMIN_USER).count() != 0:
            click.echo(f"User '{constants.DEFAULT_ADMIN_USER}' already exists.")
            return

        user = User(
            username=constants.DEFAULT_ADMIN_USER,
            password_hash=helpers.hash_password(admin_password),
            is_admin=True,
        )
        session.add(user)
        session.commit()


