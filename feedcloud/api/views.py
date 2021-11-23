import apispec
import flask
import flask_cors
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_jwt_extended import (JWTManager, create_access_token,
                                get_jwt_identity, jwt_required)

from . import schemas, services

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
    body = schema.load(flask.request.json)
    username = body["username"]
    password = body["password"]

    if not services.authenticate_user(username, password):
        resp_schema = schemas.ErrorSchema()
        return resp_schema.dump({"message": "Invalid username or password"}), 401

    response = dict(token=create_access_token(identity=username))
    return schemas.AuthResponseSchema().dump(response)


@app.route("/feeds/", methods=["POST"])
@jwt_required()
def register_feed():
    username = get_jwt_identity()
    return "hello world!"


@app.route("/swagger.json")
def create_swagger_spec():
    response = flask.jsonify(spec.to_dict())
    return response


# Register endpoints with the API Spec
with app.test_request_context():
    spec.path(view=authenticate)
