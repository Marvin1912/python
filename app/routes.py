from flask import Flask, render_template


def register(app: Flask) -> None:
    @app.route("/")
    def index():
        return render_template("index.html")
