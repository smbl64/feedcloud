from typing import Tuple

import apispec
import flask
import flask_cors
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from marshmallow.exceptions import ValidationError

from feedcloud import settings

from . import exceptions, schemas, services

app = flask.Flask(__name__)
app.config.update(settings.get_all_settings())

flask_cors.CORS(app)
jwt = JWTManager(app)
spec = apispec.APISpec(
    title="FeedCloud",
    version="1.0.0",
    openapi_version="3.0.2",
    plugins=[FlaskPlugin(), MarshmallowPlugin()],
)


@app.route("/auth/", methods=["POST"])
def authenticate():
    """
    ---
    post:
        description: Authenticate with the API
        consumes: application/json
        parameters:
            - in: body
              required: true
              schema: UserSchema
        responses:
            200:
                description: Authentication successful
                content:
                    application/json:
                        schema: AuthResponseSchema
            401:
                description: Invalid username or password
                content:
                    application/json:
                        schema: MessageSchema
            400:
                description: Invalid request
                content:
                    application/json:
                        schema: MarshmallowErrorSchema
    """
    schema = schemas.UserSchema()

    try:
        body = schema.load(flask.request.json)
        username = body["username"]
        password = body["password"]
    except ValidationError as err:
        return schemas.MarshmallowErrorSchema().dump(dict(errors=err.messages)), 400

    if not services.authenticate_user(username, password):
        return make_error("Invalid username or password")

    response = dict(token=create_access_token(identity=username))
    return schemas.AuthResponseSchema().dump(response)


def make_error(msg: str) -> Tuple[dict, int]:
    return make_message(msg), 401


def make_message(msg: str) -> dict:
    resp_schema = schemas.MessageSchema()
    return resp_schema.dump({"message": msg})


@app.route("/users/", methods=["POST"])
@jwt_required()
def create_user():
    """
    ---
    post:
        description: Create a new feed
        consumes: application/json
        parameters:
            - in: body
              required: true
              schema: UserSchema
        responses:
            201:
                description: User created successfully
                content:
                    application/json:
                        schema: MessageSchema
            409:
                description: User already exists
                content:
                    application/json:
                        schema: MessageSchema
            400:
                description: Invalid request
                content:
                    application/json:
                        schema: MarshmallowErrorSchema
            401:
                description: Unauthorized access
                content:
                    application/json:
                        schema: MessageSchema
    """
    schema = schemas.UserSchema()

    try:
        body = schema.load(flask.request.json)
    except ValidationError as err:
        return schemas.MarshmallowErrorSchema().dump(dict(errors=err.messages)), 400

    username = get_jwt_identity()
    try:
        created = services.create_new_user(username, body["username"], body["password"])
    except exceptions.AuthorizationFailedError as e:
        return make_error(str(e))

    if created:
        return make_message("Created"), 201
    else:
        return make_message("User already exists"), 409


@app.route("/feeds/", methods=["POST"])
@jwt_required()
def register_feed():
    """
    ---
    post:
        description: Register a new feed
        consumes: application/json
        parameters:
            - in: body
              required: true
              schema: MinimalFeedSchema
        responses:
            201:
                description: Feed created successfully
                content:
                    application/json:
                        schema: MessageSchema
            409:
                description: Feed already exists
                content:
                    application/json:
                        schema: MessageSchema
            400:
                description: Invalid request
                content:
                    application/json:
                        schema: MarshmallowErrorSchema
    """
    schema = schemas.MinimalFeedSchema()

    try:
        body = schema.load(flask.request.json)
    except ValidationError as err:
        return schemas.MarshmallowErrorSchema().dump(dict(errors=err.messages)), 400

    username = get_jwt_identity()
    try:
        created = services.register_feed(username, body["url"])
    except exceptions.AuthorizationFailedError as e:
        return make_error(str(e))

    if created:
        return make_message("Created"), 201
    else:
        return make_message("Feed already exists"), 409


@app.route("/feeds/<feed_id>", methods=["DELETE"])
@jwt_required()
def unregister_feed(feed_id):
    """
    ---
    delete:
        description: Unregister a feed. The feed and all its entries will be deleted.
        parameters:
            - in: path
              name: feed_id
              required: true
              schema:
                  type: integer
              description: Numberic ID of the feed to delete
        responses:
            200:
                description: Feed successfully deleted
                content:
                    application/json:
                        schema: MessageSchema
            401:
                description: Unauthorized access
                content:
                    application/json:
                        schema: MessageSchema
            404:
                description: Feed not found
                content:
                    application/json:
                        schema: MessageSchema

    """
    username = get_jwt_identity()
    try:
        deleted = services.unregister_feed(username, feed_id)
    except exceptions.AuthorizationFailedError as e:
        return make_error(str(e))

    if deleted:
        return make_message("Feed is deleted"), 200
    else:
        return make_message("Feed not found"), 404


@app.route("/feeds/<feed_id>/force-run", methods=["PUT"])
@jwt_required()
def force_run_feed(feed_id):
    """
    ---
    put:
        description: Force run a feed. Feed will be scheduled for running immediately.
        parameters:
            - in: path
              name: feed_id
              required: true
              schema:
                  type: integer
              description: Numberic ID of the feed to run
        responses:
            200:
                description: Feed successfully scheduled to be run
                content:
                    application/json:
                        schema: MessageSchema
            401:
                description: Unauthorized access
                content:
                    application/json:
                        schema: MessageSchema
            404:
                description: Feed not found
                content:
                    application/json:
                        schema: MessageSchema
    """
    username = get_jwt_identity()
    try:
        success = services.force_run_feed(username, feed_id)
    except exceptions.AuthorizationFailedError as e:
        return make_error(str(e))

    if success:
        return make_message("Accepted"), 200
    else:
        return make_message("Feed not found"), 404


@app.route("/feeds/", methods=["GET"])
@jwt_required()
def get_feeds():
    """
    ---
    get:
        description: Get the list of all registered feeds.
        responses:
            401:
                description: Unauthorized access
                content:
                    application/json:
                        schema: MessageSchema
            200:
                description: List of registered feeds
                content:
                    application/json:
                        schema: FeedListSchema
    """
    username = get_jwt_identity()
    try:
        feeds = services.get_feeds(username)
    except exceptions.AuthorizationFailedError as e:
        return make_error(str(e))

    schema = schemas.FeedListSchema()
    return schema.dump(dict(feeds=feeds)), 200


@app.route("/feeds/<feed_id>/entries/", methods=["GET"])
@jwt_required()
def get_feed_entries(feed_id):
    """
    ---
    get:
        description: Get the list of entries in a feed.
        parameters:
            - in: path
              name: feed_id
              required: true
              schema:
                  type: integer
              description: Feed ID to get the entries of
            - in: query
              name: status
              required: false
              schema:
                  type: string
              description: Filter by entry status. Can be 'read' or 'unread'.
        responses:
            401:
                description: Unauthorized access
                content:
                    application/json:
                        schema: MessageSchema
            200:
                description: List of entries belonging to the feed
                content:
                    application/json:
                        schema: EntryListSchema
    """
    username = get_jwt_identity()
    status = flask.request.args.get("status")

    try:
        entries = services.get_entries(username, feed_id=feed_id, entry_status=status)
    except (exceptions.AuthorizationFailedError, ValueError) as e:
        return make_error(str(e))

    schema = schemas.EntryListSchema()
    return schema.dump(dict(entries=entries)), 200


@app.route("/entries/<entry_id>", methods=["PUT"])
@jwt_required()
def change_entry_status(entry_id):
    """
    ---
    put:
        description: Mark an entry as read or unread.
        parameters:
            - in: body
              required: true
              schema:
                  EntryStatusChangeRequestSchema
        responses:
            400:
                description: Invalid request
                content:
                    application/json:
                        schema: MarshmallowErrorSchema
            401:
                description: Unauthorized access
                content:
                    application/json:
                        schema: MessageSchema
            200:
                description: Entry's status changed successfully
                content:
                    application/json:
                        schema: MessageSchema
            404:
                description: Entry not found
                content:
                    application/json:
                        schema: MessageSchema

    """
    username = get_jwt_identity()
    schema = schemas.EntryStatusChangeRequestSchema()
    try:
        body = schema.load(flask.request.json)
    except ValidationError as err:
        return schemas.MarshmallowErrorSchema().dump(dict(errors=err.messages)), 400

    username = get_jwt_identity()
    try:
        changed = services.change_entry_status(username, entry_id, body["status"])
    except exceptions.AuthorizationFailedError as e:
        return make_error(str(e))

    if changed:
        return make_message("Status changed successfully"), 200
    else:
        return make_message("Entry not found"), 404


@app.route("/entries/", methods=["GET"])
@jwt_required()
def get_entries():
    """
    ---
    get:
        description: Get entries across all feeds.
        parameters:
            - in: query
              name: status
              required: false
              schema:
                  type: string
              description: Filter by entry status. Can be 'read' or 'unread'.
        responses:
            401:
                description: Unauthorized access
                content:
                    application/json:
                        schema: MessageSchema
            200:
                description: List of entries belonging to the feed
                content:
                    application/json:
                        schema: EntryListSchema
    """
    username = get_jwt_identity()
    status = flask.request.args.get("status")

    try:
        entries = services.get_entries(username, entry_status=status)
    except (exceptions.AuthorizationFailedError, ValueError) as e:
        return make_error(str(e))

    schema = schemas.EntryListSchema()
    return schema.dump(dict(entries=entries)), 200


@app.route("/swagger.json")
def create_swagger_spec():
    response = flask.jsonify(spec.to_dict())
    return response


# Register endpoints with the API Spec
with app.test_request_context():
    spec.path(view=authenticate)
    spec.path(view=create_user)
    spec.path(view=register_feed)
    spec.path(view=unregister_feed)
    spec.path(view=force_run_feed)
    spec.path(view=get_feeds)
    spec.path(view=get_feed_entries)
    spec.path(view=change_entry_status)
    spec.path(view=get_entries)
