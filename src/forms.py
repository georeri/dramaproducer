from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    IntegerField,
    TextAreaField,
    DateTimeField,
    EmailField,
    SelectField,
)
from wtforms.validators import DataRequired, Regexp, UUID


class RegistrationForm(FlaskForm):
    event = SelectField("Please choose an event", validators=[UUID()])
    fist_name = StringField("First name", description="", validators=[DataRequired()])
    last_name = StringField("Last name", validators=[DataRequired()])
    corp_email = EmailField(
        "Corporate email", validators=[DataRequired(), Regexp(r"^.*@wellsfargo.com$")]
    )
    corp_id = StringField(
        "Corporate UID", validators=[DataRequired(), Regexp(r"^[a-zA-Z][0-9]{6}")]
    )
    personal_email = EmailField("Personal email")
    github_user_id = StringField("GitHub username")
