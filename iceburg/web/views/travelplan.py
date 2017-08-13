import requests
from flask import current_app
from wtforms import DecimalField, SelectField
from wtforms.validators import input_required
from flask_wtf import FlaskForm


class TravelPlanForm(FlaskForm):
    data = {}
    errors = []

    facilities = SelectField(
        'Where do you want to go?',
        coerce=int,
        description='Select the country',
    )

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.facilities.choices = [(1, 'one'), (2, 'two')]
