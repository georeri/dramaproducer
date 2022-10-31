from pathlib import Path
from flask import Flask, jsonify, make_response
from jinja2 import Environment, FileSystemLoader
from flask_wtf.csrf import CSRFProtect
from forms import RegistrationForm

ROOT_DIR = Path(__file__).parent
TEMPLATE_ROOT_DIR = ROOT_DIR.joinpath("templates")
ENV = Environment(
    loader=FileSystemLoader(TEMPLATE_ROOT_DIR),
    autoescape=True,
)
TEMPLATE = ENV.get_template("index.html")


app = Flask(__name__)
app.secret_key = ""
csrf = CSRFProtect(app)


@app.route("/")
def home():
    choices = [
        ("1", "Level Up Chandler / ASD-200-CMP / November 2022"),
        ("2", "Level Up Charlotte / ASD-200-CMP / April 2023"),
    ]
    form = RegistrationForm()
    form.event.choices = choices
    content = TEMPLATE.render(form=form)
    return content


@app.route("/api/list-members")
def list_members():
    return jsonify({})


@app.route("/api/member-status/<username>")
def member_status(username):
    return jsonify({})


@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error="Not found!"), 404)
