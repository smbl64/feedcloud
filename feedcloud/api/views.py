from typing import Tuple

import apispec
import flask
import flask_cors
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_jwt_extended import (JWTManager, create_access_token,
                                get_jwt_identity, jwt_required)
from marshmallow.exceptions import ValidationError

from . import exceptions, schemas, services

app = flask.Flask(__name__)
flask_cors.CORS(app)


# TODO
app.config["JWT_SECRET_KEY"] = "super-secret"
jwt = JWTManager(app)

spec = apispec.APISpec(
    title="FeedCloud",
    version="1.0.0",
    openapi_version="3.0.2",
    plugins=[FlaskPlugin(), MarshmallowPlugin()],
)

# spec.components.schema("AuthRequestSchema", schema=schemas.AuthRequestSchema)
# spec.components.schema("AuthResponseSchema", schema=schemas.AuthResponseSchema)
# spec.components.schema("ErrorSchema", schema=schemas.ErrorSchema)


@app.route("/auth", methods=["POST"])
def authenticate():
    """
    Authenticate with the API.
    ---
    post:
        consumes:
            application/json
        parameters:
            - in: body
              required: true
              schema: AuthRequestSchema
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
                schema: ErrorSchema
    """
    schema = schemas.AuthRequestSchema()

    try:
        body = schema.load(flask.request.json)
        username = body["username"]
        password = body["password"]
    except ValidationError as err:
        return flask.jsonify(err.messages), 400

    if not services.authenticate_user(username, password):
        return make_error("Invalid username or password")

    response = dict(token=create_access_token(identity=username))
    return schemas.AuthResponseSchema().dump(response)


def make_error(msg: str) -> Tuple[dict, int]:
    resp_schema = schemas.ErrorSchema()
    return resp_schema.dump({"message": msg}), 401


@app.route("/feeds/", methods=["POST"])
@jwt_required()
def register_feed():
    schema = schemas.FeedRegisterSchema()

    try:
        body = schema.load(flask.request.json)
    except ValidationError as err:
        return flask.jsonify(err.messages), 400

    username = get_jwt_identity()
    try:
        created = services.register_feed(username, body["url"])
    except exceptions.AuthorizationFailedError as e:
        return make_error(str(e))

    if created:
        return "Created", 201
    else:
        return "Feed already exists", 409


@app.route("/feeds/", methods=["DELETE"])
@jwt_required()
def unregister_feed():
    schema = schemas.FeedRegisterSchema()

    try:
        body = schema.load(flask.request.json)
    except ValidationError as err:
        return flask.jsonify(err.messages), 400

    username = get_jwt_identity()
    try:
        deleted = services.unregister_feed(username, body["url"])
    except exceptions.AuthorizationFailedError as e:
        return make_error(str(e))

    if deleted:
        return "", 200
    else:
        return "", 404


@app.route("/swagger.json")
def create_swagger_spec():
    response = flask.jsonify(spec.to_dict())
    return response


# Register endpoints with the API Spec
with app.test_request_context():
    spec.path(view=authenticate)
    spec.path(view=register_feed)
    spec.path(view=unregister_feed)
