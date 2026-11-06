import os

from flask import Flask


def createApp():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(16)

    from . import routes
    app.register_blueprint(routes.bp)

    from .garo import GARO_URL
    if not GARO_URL:
        print('GARO_URL är inte satt, laddboxen kan inte styras')

    from .scheduler import scheduler
    scheduler.start()

    return app
