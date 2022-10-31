import os
from pathlib import Path
from flask import Flask, jsonify, make_response, redirect
from jinja2 import Environment, FileSystemLoader
from flask_wtf.csrf import CSRFProtect
from forms import RegistrationForm

ROOT_DIR = Path(__file__).parent
TEMPLATE_ROOT_DIR = ROOT_DIR.joinpath("templates")
ENV = Environment(
    loader=FileSystemLoader(TEMPLATE_ROOT_DIR),
    autoescape=True,
)


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ARBITRARY")
csrf = CSRFProtect(app)


def render_template(template_path, *args, **kwargs):
    return ENV.get_template(template_path).render(*args, **kwargs)


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
