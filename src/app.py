import os
import uuid
from typing import Any
from pathlib import Path
from flask import Flask, jsonify, make_response, redirect
from jinja2 import Environment, FileSystemLoader
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SelectField, HiddenField
from wtforms import validators
import pynamodb.constants
from botocore.exceptions import ClientError
from pynamodb.exceptions import UpdateError
from pynamodb.attributes import Attribute
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
# Custom table attributes
#########################


class UUIDAttribute(Attribute[uuid.UUID]):
    """
    PynamoDB attribute to for UUIDs. These are backed by DynamoDB unicode (`S`) types.
    """

    attr_type = pynamodb.constants.STRING

    def __init__(self, remove_dashes: bool = False, **kwargs: Any) -> None:
        """
        Initializes a UUIDAttribute object.
        :param remove_dashes: if set, the string serialization will be without dashes.
        Defaults to False.
        """
        super().__init__(**kwargs)
        self._remove_dashes = remove_dashes

    def serialize(self, value: uuid.UUID) -> str:
        result = str(value)

        if self._remove_dashes:
            result = result.replace("-", "")

        return result

    def deserialize(self, value: str) -> uuid.UUID:
        return uuid.UUID(value)


#########################
# DynamoDB table models
#########################


class EventModel(Model):
    class Meta:
        table_name = "levelup-events"
        region = "us-east-1"
        stream_view_type = STREAM_NEW_AND_OLD_IMAGE
        billing_mode = PAY_PER_REQUEST_BILLING_MODE

    uid = UUIDAttribute(hash_key=True, default_for_new=uuid.uuid4)
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

    uid = UUIDAttribute(hash_key=True, default_for_new=uuid.uuid4)
    event_uid = UUIDAttribute()
    status = UnicodeAttribute(default="new")
    first_name = UnicodeAttribute()
    last_name = UnicodeAttribute()
    corp_email = UnicodeAttribute()
    corp_sid = UnicodeAttribute()
    personal_email = UnicodeAttribute(null=True)
    github_username = UnicodeAttribute(null=True)


#########################
# Form definitions
#########################


class RegistrationForm(FlaskForm):
    event = SelectField(
        "Please choose an event",
        description="Click the box above to choose an event",
        validators=[validators.UUID()],
    )
    first_name = StringField("First name", validators=[validators.DataRequired()])
    last_name = StringField("Last name", validators=[validators.DataRequired()])
    corp_email = EmailField(
        "Corporate email",
        description="Must be a valid @wellsfargo.com address",
        validators=[
            validators.DataRequired(),
            validators.Regexp(r"^.*@wellsfargo.com$"),
        ],
    )
    corp_sid = StringField(
        "Corporate SID",
        description="Your enterprise login ID in the form of 'X000000'",
        validators=[
            validators.DataRequired(),
            validators.Length(max=7),
            validators.Regexp(r"^[a-zA-Z][0-9]{6}"),
        ],
    )
    personal_email = EmailField(
        "Personal email",
        description="By providing this you consent to receiving communications",
    )
    github_username = StringField(
        "GitHub username",
        description="Your public GitHub (non-Wells Fargo) username",
    )

    def save(self):
        RegistrationModel(
            event_uid=self.event.data,
            first_name=self.first_name.data,
            last_name=self.last_name.data,
            corp_email=self.corp_email.data,
            corp_sid=self.corp_sid.data,
            personal_email=self.personal_email.data,
            github_username=self.github_username.data,
        ).save()


class CancellationForm(FlaskForm):
    registration = HiddenField(validators=[validators.UUID()])


#########################
# Helper functions
#########################


def is_conditional_error(e):
    if isinstance(e.cause, ClientError):
        code = e.cause.response["Error"].get("Code")
        if code == "ConditionalCheckFailedException":
            return True


def create_all_tables():
    if not EventModel.exists():
        EventModel.create_table(wait=True)

    if not RegistrationModel.exists():
        RegistrationModel.create_table(wait=True)


def get_open_events():
    events = [e for e in EventModel.scan() if e.status == "open"]
    return sorted(events, key=lambda e: e.start_date)


def get_event_registrations(event):
    registrations = [
        r
        for r in RegistrationModel.scan()
        if r.event_uid == event.uid  # and r.status != "cancelled"
    ]
    return sorted(registrations, key=lambda r: r.last_name)


def render_template(template_path, *args, **kwargs):
    return ENV.get_template(template_path).render(*args, **kwargs)


#########################
# Flask (API) routes
#########################


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")


@app.route("/", methods=["GET", "POST"])
def home():
    form = RegistrationForm()
    form.event.choices = [(str(e.uid), e.name) for e in get_open_events()]
    if form.validate_on_submit():
        form.save()
        return redirect("/registration_success")
    return render_template("index.html", form=form)


@app.route("/registration_success", methods=["GET"])
def registration_success():
    return render_template("registration_success.html")


@app.route("/view/<uuid:registration_id>", methods=["GET"])
def view_registration(registration_id):
    registration = RegistrationModel.get(registration_id)
    event = EventModel.get(registration.event_uid)
    form = CancellationForm(registration=registration.uid)
    return render_template(
        "registration_details.html",
        registration=registration,
        event=event,
        form=form,
    )


@app.route("/cancel/<uuid:registration_id>", methods=["POST"])
def cancel_registration(registration_id):
    registration = RegistrationModel.get(registration_id)
    registration.update(actions=[RegistrationModel.status.set("cancelled")])
    return render_template("registration_cancelled.html")


@app.route("/check-in/<uuid:registration_id>", methods=["GET"])
def event_checkin(registration_id):
    registration = RegistrationModel.get(registration_id)
    try:
        registration.update(
            actions=[RegistrationModel.status.set("attended")],
            condition=(RegistrationModel.status != "cancelled")
            & (RegistrationModel.status != "attended"),
        )
        result = (
            f"Thanks {registration.first_name.capitalize()}, you are all checked-in!"
        )
    except UpdateError as e:
        if is_conditional_error(e):
            result = f"Sorry {registration.first_name.capitalize()}, you can't check-in because this registration is marked as <i>'{registration.status}'</i>"
    return render_template("attendance.html", result=result)


@app.route("/roster/<uuid:event_id>", methods=["GET"])
def event_roster(event_id):
    event = EventModel.get(event_id)
    registrations = get_event_registrations(event)
    return render_template("roster.html", registrations=registrations)
