from marshmallow import Schema, fields
from marshmallow.validate import OneOf

from feedcloud import database


class AuthRequestSchema(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)


class AuthResponseSchema(Schema):
    token = fields.String(required=True)


class MessageSchema(Schema):
    message = fields.String(required=True)


class MinimalFeedSchema(Schema):
    url = fields.String(required=True)


class FeedSchema(Schema):
    id = fields.Integer(required=True)
    url = fields.String(required=True)


class FeedListSchema(Schema):
    feeds = fields.Nested(FeedSchema, many=True)


class EntrySchema(Schema):
    id = fields.Integer()
    original_id = fields.String()
    title = fields.String()
    summary = fields.String()
    link = fields.String()
    published_at = fields.DateTime()
    feed_id = fields.Integer()
    status = fields.String()


class EntryListSchema(Schema):
    entries = fields.Nested(EntrySchema, many=True)


class EntryStatusChangeRequestSchema(Schema):
    status = fields.String(required=True, validate=OneOf(database.Entry.STATUS_LIST))


class MarshmallowErrorSchema(Schema):
    errors = fields.Mapping(keys=fields.String(), values=fields.List(fields.String))
