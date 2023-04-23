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
# from decorators import authentication_required, admin_required
from forms import (
    ProductionForm, ProductionUpdateForm
)
from models import ProductionModel

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
# app.config["AWS_COGNITO_DOMAIN"] = CONST.COGNITO_DOMAIN
# app.config["AWS_COGNITO_USER_POOL_ID"] = CONST.COGNITO_USER_POOL_ID
# app.config["AWS_COGNITO_USER_POOL_CLIENT_ID"] = CONST.COGNITO_USER_POOL_CLIENT_ID
# app.config[
#     "AWS_COGNITO_USER_POOL_CLIENT_SECRET"
# ] = CONST.COGNITO_USER_POOL_CLIENT_SECRET
# app.config["AWS_COGNITO_REDIRECT_URL"] = CONST.COGNITO_REDIRECT_URL

CORS(app)
# CSRFProtect(app)
# aws_auth = AWSCognitoAuthentication(app)
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

def get_open_productions():
    productions = [e for e in ProductionModel.scan() if e.status == "open"]
    return sorted(productions, key=lambda e: e.start_date)

def render_template(template_path, *args, **kwargs):
    return ENV.get_template(template_path).render(*args, **kwargs, request=request)

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


@app.route("/admin/", methods=["GET"])
# @admin_required
def admin_home():
    return render_template("admin.html")


@app.route("/admin/production/", methods=["GET", "POST"])
# @admin_required
def production_create():
    form = ProductionForm()
    form.status.choices = [(i, i) for i in ["open", "closed", "done"]]
    if form.validate_on_submit():
        production = form.save()
        return redirect(f"/admin/production/{production.uid}")
    return render_template(
        "production_create.html",
        form=form,
    )


@app.route("/admin/production/<uuid:production_id>", methods=["GET"])
# @admin_required
def production_details(production_id):
    production = ProductionModel.get(production_id)
    return render_template(
        "production_details.html", production=production
    )


@app.route("/admin/productions/", methods=["GET"])
# @admin_required
def production_list():
    productions = ProductionModel.scan()
    return render_template("production_list.html", productions=productions)


@app.route("/admin/production/<uuid:production_id>/edit/", methods=["GET", "POST"])
# @admin_required
def production_edit(production_id):
    production = ProductionModel().get(production_id)
    form = ProductionUpdateForm(data=production.attribute_values)
    form.status.choices = [(i, i) for i in ["open", "closed", "done"]]
    if form.validate_on_submit():
        form.save()
        return redirect(f"/admin/production/{production_id}")
    return render_template("production_edit.html", form=form)


@app.route("/admin/production/<uuid:production_id>/delete/", methods=["POST"])
# @admin_required
def production_delete(production_id):
    production = ProductionModel().get(production_id)
    production.delete()
    return redirect("/admin/productions/")


#########################
# Authentication routes
#########################


# @app.route("/login")
# def login():
#     return redirect(aws_auth.get_sign_in_url())


# @app.route("/logout")
# def logout():
#     response = redirect("/loggedout")
#     unset_access_cookies(response)
#     return response


# @app.route("/loggedout")
# def logged_out():
#     return render_template("logout.html")


# @app.route("/aws_cognito_redirect", methods=["GET"])
# def aws_cognito_redirect():
#     access_token = aws_auth.get_access_token(request.args)
#     response = redirect("/")
#     set_access_cookies(response, access_token, max_age=60 * 60)
#     return response
