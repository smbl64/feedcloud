from marshmallow import Schema, fields


class AuthRequestSchema(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)


class AuthResponseSchema(Schema):
    token = fields.String(required=True)


class ErrorSchema(Schema):
    message = fields.String(required=True)


class FeedRegisterSchema(Schema):
    url = fields.String(required=True)
