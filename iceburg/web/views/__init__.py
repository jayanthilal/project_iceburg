import logging

from flask import render_template, Blueprint, jsonify, request, Response
from iceburg.web.config import Config

LOGGER = logging.getLogger(__name__)

app = Blueprint('web', __name__)


@app.route('/')
def index():
    return render_template('index.html', api_url=Config.API_URL)
