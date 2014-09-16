import os

import flask
from flaskext.sqlalchemy import SQLAlchemy

app = flask.Flask(__name__)
db = SQLAlchemy(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

# DATABASE_URL

if not os.environ.get('DEV'):
    app.config['SQLALCHEMY_ECHO'] = False
    app.debug = True
