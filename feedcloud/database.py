import sqlalchemy as sa
import sqlalchemy.orm
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from feedcloud import settings

engine = None
Base = declarative_base()
Session = sessionmaker()


class User(Base):
    __tablename__ = "user"
    __table_args__ = (sa.UniqueConstraint("username", name="username_idx"),)

    id = sa.Column(sa.Integer, primary_key=True)
    username = sa.Column(sa.Text, nullable=False)
    password_hash = sa.Column(sa.Text, nullable=False)
    is_admin = sa.Column(sa.Boolean, nullable=False, default=False)

    feeds = relationship("Feed", back_populates="user", passive_deletes=True)


class Feed(Base):
    __tablename__ = "feed"

    id = sa.Column(sa.Integer, primary_key=True)
    url = sa.Column(sa.Text, nullable=False)

    user_id = sa.Column(
        sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", back_populates="feeds")

    entries = relationship("Entry", back_populates="feed", passive_deletes=True)
    update_runs = relationship(
        "FeedUpdateRun", back_populates="feed", passive_deletes=True
    )


class FeedUpdateRun(Base):
    FAILED = "failed"
    SUCCESS = "success"
    STATUS_LIST = (FAILED, SUCCESS)

    __tablename__ = "feed_update_run"
    __table_args__ = (sa.Index("feed_timestamp_idx", "feed_id", sa.desc("timestamp")),)

    id = sa.Column(sa.Integer, primary_key=True)
    timestamp = sa.Column(sa.DateTime, nullable=False)
    status = sa.Column(sa.Text, nullable=False)
    failure_count = sa.Column(sa.Integer, nullable=False, default=0)
    next_run_schedule = sa.Column(sa.DateTime)

    n_downloaded = sa.Column(sa.Integer, nullable=False, default=0)
    n_ignored = sa.Column(sa.Integer, nullable=False, default=0)

    feed_id = sa.Column(
        sa.Integer, sa.ForeignKey("feed.id", ondelete="CASCADE"), nullable=False
    )
    feed = relationship("Feed", back_populates="update_runs")


class Entry(Base):
    UNREAD = "unread"
    READ = "read"
    STATUS_LIST = (UNREAD, READ)

    __tablename__ = "entry"
    __table_args__ = (
        sa.UniqueConstraint("original_id", "feed_id", name="original_id_feed_idx"),
    )

    id = sa.Column(sa.Integer, primary_key=True)

    original_id = sa.Column(sa.Text, nullable=False)
    title = sa.Column(sa.Text, nullable=False)
    summary = sa.Column(sa.Text, nullable=False)
    link = sa.Column(sa.Text, nullable=False)
    saved_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    published_at = sa.Column(sa.DateTime, nullable=False)

    status = sa.Column(sa.Text, nullable=False, default=UNREAD)

    feed_id = sa.Column(
        sa.Integer, sa.ForeignKey("feed.id", ondelete="CASCADE"), nullable=False
    )
    feed = relationship("Feed", back_populates="entries")


def configure():
    global engine
    if not engine:
        engine = sa.create_engine(settings.DATABASE_URL, echo=False)
        Session.configure(bind=engine)


def drop_all():
    configure()
    Base.metadata.drop_all(engine)


def create_all():
    configure()
    Base.metadata.create_all(engine)


def get_session() -> sqlalchemy.orm.Session:
    configure()
    return Session()
