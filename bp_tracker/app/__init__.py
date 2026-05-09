"""Flask app factory: load env, init DB pool, bootstrap schema, register routes."""

import logging

from dotenv import load_dotenv
from flask import Flask

from . import db, routes


def create_app() -> Flask:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    db.init_pool()
    db.bootstrap_schema()
    routes.register(app)
    return app
