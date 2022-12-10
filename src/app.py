import io
import logging
import sys
from pathlib import Path

import segno
from botocore.exceptions import ClientError
from flask import Flask, redirect, request
from flask_awscognito import AWSCognitoAuthentication
from flask_cors import CORS
from flask_jwt_extended import JWTManager, set_access_cookies, unset_access_cookies

# from flask_wtf.csrf import CSRFProtect
from jinja2 import Environment, FileSystemLoader
from pynamodb.exceptions import UpdateError

import constants as CONST
from decorators import authentication_required, admin_required
from forms import (
    CancellationForm,
    EventForm,
    EventUpdateForm,
    RegistrationEditForm,
    RegistrationForm,
    SearchForm,
    TeamForm,
)
from models import EventModel, RegistrationModel, TeamModel

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

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = CONST.SECRET_KEY
app.url_map.strict_slashes = False
app.config["AWS_DEFAULT_REGION"] = CONST.AWS_DEFAULT_REGION
app.config["AWS_COGNITO_DOMAIN"] = CONST.COGNITO_DOMAIN
app.config["AWS_COGNITO_USER_POOL_ID"] = CONST.COGNITO_USER_POOL_ID
app.config["AWS_COGNITO_USER_POOL_CLIENT_ID"] = CONST.COGNITO_USER_POOL_CLIENT_ID
app.config[
    "AWS_COGNITO_USER_POOL_CLIENT_SECRET"
] = CONST.COGNITO_USER_POOL_CLIENT_SECRET
app.config["AWS_COGNITO_REDIRECT_URL"] = CONST.COGNITO_REDIRECT_URL

CORS(app)
# CSRFProtect(app)
aws_auth = AWSCognitoAuthentication(app)
jwt = JWTManager(app)
app.create_jinja_environment()

#########################
# Helper functions
#########################


def is_conditional_error(e):
    if isinstance(e.cause, ClientError):
        code = e.cause.response["Error"].get("Code")
        if code == "ConditionalCheckFailedException":
            return True


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
    return ENV.get_template(template_path).render(*args, **kwargs, request=request)


def makeQR(value):
    url = f"{CONST.SITE_URL}/registration/{str(value)}/check-in/"
    qrcode = segno.make(url)
    buff = io.BytesIO()
    qrcode.save(buff, kind="svg", xmldecl=False, scale=2)
    byte_str = buff.getvalue()
    text_obj = byte_str.decode("UTF-8")
    return text_obj


ENV.filters["makeQR"] = makeQR

#########################
# Flask (API) routes
#########################


@app.errorhandler(401)
def custom_401(error):
    return render_template("401.html")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html")


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def create_registration():
    form = RegistrationForm(data=request.args)
    form.event.choices = [(str(e.uid), e.name) for e in get_open_events()]
    if form.validate_on_submit():
        form.save()
        return render_template("registration_success.html")
    return render_template("registration_create.html", form=form)


@app.route("/registration/<uuid:registration_id>/", methods=["GET"])
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


@app.route("/registration/<uuid:registration_id>/edit/", methods=["GET", "POST"])
def edit_registration(registration_id):
    registration = RegistrationModel.get(registration_id)
    form = RegistrationEditForm(data=registration.attribute_values)
    form.event.choices = [(str(e.uid), e.name) for e in get_open_events()]
    if form.validate_on_submit():
        form.save()
        return redirect(f"/registration/{registration_id}")
    return render_template("registration_edit.html", form=form)


@app.route("/admin/", methods=["GET"])
@admin_required
def admin_home():
    return render_template("admin.html")


@app.route("/admin/event/", methods=["GET", "POST"])
@admin_required
def event_create():
    form = EventForm()
    form.status.choices = [(i, i) for i in ["open", "closed", "done"]]
    if form.validate_on_submit():
        event = form.save()
        return redirect(f"/admin/event/{event.uid}")
    return render_template(
        "event_create.html",
        form=form,
    )


@app.route("/admin/event/<uuid:event_id>", methods=["GET"])
@admin_required
def event_details(event_id):
    event = EventModel.get(event_id)
    registrations = get_event_registrations(event)
    return render_template(
        "event_details.html", registrations=registrations, event=event
    )


@app.route("/admin/events/", methods=["GET"])
@admin_required
def event_list():
    events = EventModel.scan()
    return render_template("event_list.html", events=events)


@app.route("/admin/event/<uuid:event_id>/edit/", methods=["GET", "POST"])
@admin_required
def event_edit(event_id):
    event = EventModel().get(event_id)
    form = EventUpdateForm(data=event.attribute_values)
    form.status.choices = [(i, i) for i in ["open", "closed", "done"]]
    if form.validate_on_submit():
        form.save()
        return redirect(f"/admin/event/{event_id}")
    return render_template("event_edit.html", form=form)


@app.route("/admin/event/<uuid:event_id>/delete/", methods=["POST"])
@admin_required
def event_delete(event_id):
    event = EventModel().get(event_id)
    event.delete()
    return redirect("/admin/events/")


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
    teams = sorted(TeamModel.scan(), key=lambda x: x.team_number)
    return render_template("team_list.html", teams=teams)


@app.route("/registration/none-found", methods=["GET"])
def none_found():
    return render_template("search_no_results.html")


@app.route("/search/", methods=["GET", "POST"])
def search_registration():
    form = SearchForm()
    form.event.choices = [(str(e.uid), e.name) for e in get_open_events()]
    if form.validate_on_submit():
        r = form.save()
        if r is not None:
            return redirect(f"/registration/{r.uid}")
        else:
            return redirect("/registration/none-found")
    return render_template("search_registration.html", form=form)


#########################
# Authentication routes
#########################


@app.route("/login")
def login():
    return redirect(aws_auth.get_sign_in_url())


@app.route("/logout")
def logout():
    response = redirect("/loggedout")
    unset_access_cookies(response)
    return response


@app.route("/loggedout")
def logged_out():
    return render_template("logout.html")


@app.route("/aws_cognito_redirect", methods=["GET"])
def aws_cognito_redirect():
    access_token = aws_auth.get_access_token(request.args)
    response = redirect("/")
    set_access_cookies(response, access_token, max_age=60 * 60)
    return response
