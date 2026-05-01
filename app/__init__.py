from flask import Flask
from dotenv import load_dotenv


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    from . import routes
    routes.register(app)

    return app
