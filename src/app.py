import os, io, uuid
from typing import Any
from pathlib import Path
from datetime import datetime
from datetime import timezone
from flask import Flask, jsonify, make_response, redirect
from jinja2 import Environment, FileSystemLoader
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    EmailField,
    SelectField,
    HiddenField,
    IntegerField,
    RadioField,
)
from wtforms import validators
import pynamodb.constants
from botocore.exceptions import ClientError
from pynamodb.exceptions import UpdateError
from pynamodb.models import Model
from pynamodb.constants import STREAM_NEW_AND_OLD_IMAGE, PAY_PER_REQUEST_BILLING_MODE
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    UTCDateTimeAttribute,
    BooleanAttribute,
    MapAttribute,
    Attribute,
    ListAttribute,
)
import segno

#########################
# CONSTANTS
#########################

ROOT_DIR = Path(__file__).parent
TEMPLATE_ROOT_DIR = ROOT_DIR.joinpath("templates")
ENV = Environment(
    loader=FileSystemLoader(TEMPLATE_ROOT_DIR),
    autoescape=True,
)
REGISTRATION_STATES = {
    "registered": ["cancelled", "attended"],
    "attended": ["cancelled"],
    "cancelled": [],
}

#########################
# Setup
#########################

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ARBITRARY")
# csrf = CSRFProtect(app)


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
    six_week_comms_sent = BooleanAttribute(default=False)
    two_week_comms_sent = BooleanAttribute(default=False)
    next_week_comms_sent = BooleanAttribute(default=False)
    close_comms_sent = BooleanAttribute(default=False)


class StateTransitionError(Exception):
    pass


class RegistrationModel(Model):
    class Meta:
        table_name = "levelup-registration"
        region = "us-east-1"
        billing_mode = PAY_PER_REQUEST_BILLING_MODE
        stream_view_type = STREAM_NEW_AND_OLD_IMAGE

    uid = UUIDAttribute(hash_key=True, default_for_new=uuid.uuid4)
    event_uid = UUIDAttribute()
    status = UnicodeAttribute(default="registered")
    first_name = UnicodeAttribute()
    last_name = UnicodeAttribute()
    corp_email = UnicodeAttribute()
    corp_sid = UnicodeAttribute()
    personal_email = UnicodeAttribute(null=True)
    github_username = UnicodeAttribute(null=True)

    def can_transition_to(self, target_state):
        return target_state in REGISTRATION_STATES.get(self.status, [])

    def transition_to(self, target_state):
        if self.can_transition_to(target_state):
            self.status = target_state
        else:
            raise StateTransitionError(
                f"Can't transition from {self.status} to {target_state}"
            )


class TeamModel(Model):
    class Meta:
        table_name = "levelup-teams"
        region = "us-east-1"
        stream_view_type = STREAM_NEW_AND_OLD_IMAGE
        billing_mode = PAY_PER_REQUEST_BILLING_MODE

    team_number = NumberAttribute(hash_key=True)
    name = UnicodeAttribute()
    num_members = NumberAttribute()
    tech_stack = UnicodeAttribute()
    repo_url = UnicodeAttribute(null=True)
    env_urls = ListAttribute(null=True)


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
        e = EventModel.get(self.event.data)
        r = RegistrationModel(
            event_uid=self.event.data,
            first_name=self.first_name.data,
            last_name=self.last_name.data,
            corp_email=self.corp_email.data,
            corp_sid=self.corp_sid.data,
            personal_email=self.personal_email.data,
            github_username=self.github_username.data,
            status="attended"
            if e.start_date
            < datetime.utcnow().replace(tzinfo=timezone.utc)
            < e.end_date
            else "registered",
        )
        r.save()
        return r


class CancellationForm(FlaskForm):
    registration = HiddenField(validators=[validators.UUID()])


class TeamForm(FlaskForm):
    table_number = IntegerField(
        "Table number",
        description="Table number",
        validators=[
            validators.DataRequired(),
            validators.NoneOf(sorted([t.team_number for t in TeamModel.scan()])),
        ],
    )
    team_name = StringField(
        "Team Name",
        description="Name of your team",
        validators=[validators.DataRequired()],
    )
    num_members = IntegerField(
        "Number of members",
        description="Total number of people on the team (4-7)",
        validators=[validators.DataRequired(), validators.NumberRange(min=4, max=7)],
    )
    tech_stack = RadioField(
        "Choose a tech stack",
        validators=[validators.DataRequired()],
        choices=[("dotnet", "C#"), ("java", "Java"), ("python", "Python")],
    )

    def save(self):
        t = TeamModel(
            team_number=self.table_number.data,
            name=self.team_name.data,
            num_members=self.num_members.data,
            tech_stack=self.tech_stack.data,
        )
        t.save()
        return t


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

    if not TeamModel.exists():
        TeamModel.create_table(wait=True)


def get_open_events():
    events = [e for e in EventModel.scan() if e.status == "open"]
    return sorted(events, key=lambda e: e.start_date)


def get_event_registrations(event):
    registrations = [
        r
        for r in RegistrationModel.scan()
        if r.event_uid == event.uid and r.status != "cancelled"
    ]
    return sorted(registrations, key=lambda r: r.last_name)


def render_template(template_path, *args, **kwargs):
    return ENV.get_template(template_path).render(*args, **kwargs)


def makeQR(value, prefix=""):
    qrcode = segno.make(prefix + str(value))
    buff = io.BytesIO()
    qrcode.save(buff, kind="svg", xmldecl=False, scale=2)
    byte_str = buff.getvalue()
    text_obj = byte_str.decode("UTF-8")
    return text_obj


ENV.filters["makeQR"] = makeQR

#########################
# Flask (API) routes
#########################


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html")


@app.route("/", methods=["GET", "POST"])
def home():
    form = RegistrationForm()
    form.event.choices = [(str(e.uid), e.name) for e in get_open_events()]
    if form.validate_on_submit():
        form.save()
        return render_template("registration_success.html")
    return render_template("index.html", form=form)


@app.route("/registration", methods=["PUT"])
def create_registration_api():
    form = RegistrationForm(meta={"csrf": False})
    form.event.choices = [(str(e.uid), e.name) for e in get_open_events()]
    if form.validate_on_submit():
        form.save()
        return jsonify(form.data)
    return jsonify({"errors": form.errors})


@app.route("/registration/<uuid:registration_id>", methods=["GET"])
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


@app.route("/registration/<uuid:registration_id>", methods=["POST"])
def cancel_registration(registration_id):
    registration = RegistrationModel.get(registration_id)
    registration.update(actions=[RegistrationModel.status.set("cancelled")])
    return render_template("registration_cancelled.html")


@app.route("/registration/<uuid:registration_id>/check-in/", methods=["GET"])
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
    return render_template("checkin.html", result=result)


@app.route("/event/<uuid:event_id>", methods=["GET"])
def event_roster(event_id):
    event = EventModel.get(event_id)
    registrations = get_event_registrations(event)
    return render_template(
        "event_details.html", registrations=registrations, event=event
    )


@app.route("/events/", methods=["GET"])
def event_list():
    events = EventModel.scan()
    return render_template("event_list.html", events=events)


@app.route("/team", methods=["GET", "POST"])
def team_create():
    form = TeamForm()
    if form.validate_on_submit():
        t = form.save()
        return redirect(f"/team/{t.team_number}")
    return render_template("team_registration.html", form=form)


@app.route("/team/<int:team_number>", methods=["GET"])
def team_details(team_number):
    team = TeamModel.get(team_number)
    return render_template("team_details.html", team=team)


@app.route("/teams/", methods=["GET"])
def team_list():
    teams = TeamModel.scan()
    return render_template("team_list.html", teams=teams)
