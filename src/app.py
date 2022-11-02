import os
import uuid
from pathlib import Path
from flask import Flask, jsonify, make_response, redirect
from jinja2 import Environment, FileSystemLoader
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SelectField
from wtforms.validators import DataRequired, Regexp, UUID, Length
from pynamodb.models import Model
from pynamodb.constants import STREAM_NEW_AND_OLD_IMAGE, PAY_PER_REQUEST_BILLING_MODE
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, UTCDateTimeAttribute

#########################
# CONSTANTS
#########################

ROOT_DIR = Path(__file__).parent
TEMPLATE_ROOT_DIR = ROOT_DIR.joinpath("templates")
ENV = Environment(
    loader=FileSystemLoader(TEMPLATE_ROOT_DIR),
    autoescape=True,
)

#########################
# Setup
#########################

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ARBITRARY")
csrf = CSRFProtect(app)


#########################
# DynamoDB Models
#########################


class EventModel(Model):
    class Meta:
        table_name = "levelup-events"
        region = "us-east-1"
        stream_view_type = STREAM_NEW_AND_OLD_IMAGE
        billing_mode = PAY_PER_REQUEST_BILLING_MODE

    uid = UnicodeAttribute(hash_key=True, default_for_new=uuid.uuid4)
    name = UnicodeAttribute()
    description = UnicodeAttribute()
    location = UnicodeAttribute()
    ics_file_location = UnicodeAttribute()
    num_seats = NumberAttribute()
    start_date = UTCDateTimeAttribute()
    end_date = UTCDateTimeAttribute()
    local_time_zone = UnicodeAttribute()
    status = UnicodeAttribute(default="open")


class RegistrationModel(Model):
    class Meta:
        table_name = "levelup-registration"
        region = "us-east-1"
        billing_mode = PAY_PER_REQUEST_BILLING_MODE
        stream_view_type = STREAM_NEW_AND_OLD_IMAGE

    uid = UnicodeAttribute(hash_key=True, default_for_new=uuid.uuid4)
    status = UnicodeAttribute(default="new")
    event_uid = UnicodeAttribute()
    first_name = UnicodeAttribute()
    last_name = UnicodeAttribute()
    corp_email = UnicodeAttribute()
    corp_sid = UnicodeAttribute()
    personal_email = UnicodeAttribute(null=True)
    github_username = UnicodeAttribute(null=True)


#########################
# Form Definitions
#########################


class RegistrationForm(FlaskForm):
    event = SelectField("Please choose an event", validators=[UUID()])
    fist_name = StringField("First name", description="", validators=[DataRequired()])
    last_name = StringField("Last name", validators=[DataRequired()])
    corp_email = EmailField(
        "Corporate email", validators=[DataRequired(), Regexp(r"^.*@wellsfargo.com$")]
    )
    corp_id = StringField(
        "Corporate UID",
        validators=[DataRequired(), Length(max=7), Regexp(r"^[a-zA-Z][0-9]{6}")],
    )
    personal_email = EmailField("Personal email")
    github_user_id = StringField("GitHub username")

    def save(self):
        pass


#########################
# Helpers
#########################


def create_all_tables():
    if not EventModel.exists():
        EventModel.create_table(wait=True)

    if not RegistrationModel.exists():
        RegistrationModel.create_table(wait=True)


def render_template(template_path, *args, **kwargs):
    return ENV.get_template(template_path).render(*args, **kwargs)


#########################
# API Routes
#########################


@app.route("/", methods=["GET", "POST"])
def home():
    choices = [
        (
            "e50de23c-c91b-4bb6-885a-70090768f3d9",
            "Level Up Chandler / ASD-200-CMP / November 2022",
        ),
        (
            "5e654ff9-8550-4b13-9915-2f2fb2ef4ecd",
            "Level Up Charlotte / ASD-200-CMP / April 2023",
        ),
    ]
    form = RegistrationForm()
    form.event.choices = choices
    if form.validate_on_submit():
        return redirect("/registration_success")
    return render_template("index.html", form=form)


@app.route("/registration_success", methods=["GET"])
def registration_success():
    return render_template("success.html")
