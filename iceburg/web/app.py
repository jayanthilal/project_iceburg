import os

from flask import Flask


def create_app(debug=False):

    app = Flask(__name__)
    app.debug = debug

    app.config.from_object('iceburg.web.config.Config')

    # import the web services
    from iceburg.web import views
    app.register_blueprint(views.app)

    return app