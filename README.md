# FeedCloud

FeedCloud is an RSS scraper application which saves RSS feeds to its database and allows end-users to use the API to read feed entries and manage their own feeds.

## Running the server

You can use Docker and Docker Compose to run the server and interact with the API. To do so, run the following command:

```
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

This should automatically build / download the required Docker images and start the service.

`docker-compose.yml` file contains the base services (PostgreSQL and RabbitMQ), while `docker-compose-prod.yml` defines the FeedCloud specific services. All FeedCloud services share the same Docker image which is defined by `Dockerfile` in the repository. These are the services defined for FeedCloud:

- `init-db`: This command will make sure that the tables exist in the database and a root user is created. The default admin user and password is `root`/`root`.
- `api`: This service runs the API. The API server will listen on the port `5000`. 
- `dramatiq-worker`: FeedCloud uses Dramatiq for managing its background tasks. This will run Dramatiq workers.
- `scheduler`: FeedCloud has a dedicated daemon for picking up feeds and scheduling them for download. This Docker service starts that daemon.

**API Endpoints**

By default the server listens on `127.0.0.1:5000` for requests. Below is a list of HTTP endpoints available:

- `GET /swagger.json`: This is the OpenAPI specification of the endpoints.
- `POST /auth/`: Must be used logging in and getting a JWT token. This token must be used when calling other endpoints. Token should be passed via HTTP headers: `Authorization:"Bearer <your token>"`.

All of the endpoints are documented in the code and in the OpenAPI specification. So I won't repeat the comments here.

- `POST /feeds/`
- `DELETE /feeds/<feed_id>`
- `GET /feeds/`
- `PUT /feeds/<feed_id>/force-run`
- `GET /feeds/<feed_id>/entries/`
- `GET /entries/`
- `PUT /entries/<entry_id>`
- `POST /users/`

## Running the tests

First create a Python virtual environment and install the dependencies. Python 3.7+ is required.

```
python3 -m virtualenv .venv
source .venv/bin/activate
pip install requirements/prod.txt
```

Then run the required base services (PostgreSQL and RabbitMQ):

```
docker-compose -f docker-compose.yml up -d
```

And finally use `pytest` to run the test suite:

```
pytest -vv
```

## Design

The project consists of two main packages: `api` and `ingest`.

**feedcloud.api**

API endpoints use `Flask` and `Marshmallow`  to incoming HTTP requests. Also `apispec` package is used to generate OpenAPI documentation. 

**feedcloud.ingest**

Downloading entries for a feed happen in the background using `dramatiq` and RabbitMQ. On predefined intervals, `FeedScheduler` finds the feeds that need to updated and creates `dramatiq` jobs for each of them.

## Further improvements

I have tried to cover all the main points mentioned in the assignment. But like any other project, there is room for improvement. Below I have listed some of them:

- Right now there is no pagination for feed entries and all of them are being returned to the user.
- More test cases can be added to verify that `mashmallow` rejects invalid requests properly.
- When a feed fails permanently (i.e. the exponential backoff mechanism), FeedCloud needs to send a notification to the user. Right now the app just logs a message in console indicating that it is "informing" the user. I didn't spent time for implementing a email notification system.
- I have made sure that the whole codebase passes the `flake8` checks and the code is formatted with `black`. There is a script in `scripts/run-linters` to help with it. That being said, I think more type hints can be added to the project and then `mypy` can be used to validate them.
- With current design, every user can define the same feed and have the entries separately. An alternative design would have been to share a feed among users. When a user requests to register with a feed, we will create a subscription record between the user and that feed. Also, an additional model is required to keep track of which entries a user has "read" (because entries won't be exclusive to the user anymore).
