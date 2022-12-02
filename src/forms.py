from datetime import datetime, timezone

from flask_wtf import FlaskForm
from wtforms import (
    DateTimeLocalField,
    EmailField,
    HiddenField,
    IntegerField,
    RadioField,
    SelectField,
    StringField,
    TextAreaField,
    validators,
)
from wtforms.validators import Optional

from models import EventModel, RegistrationModel, TeamModel

#########################
# Form definitions
#########################


class EventForm(FlaskForm):
    name = StringField("Event name", validators=[validators.DataRequired()])
    description = TextAreaField("Description", validators=[validators.DataRequired()])
    location = StringField(
        "Location",
        description="Please be as specific as possible",
        validators=[validators.DataRequired()],
    )
    ics_file_location = StringField(
        "iCal invite location", validators=[validators.DataRequired()]
    )
    num_seats = IntegerField(
        "Number of seats",
        validators=[validators.DataRequired(), validators.NumberRange(min=1, max=500)],
    )
    start_date = DateTimeLocalField(
        "Start date & time",
        format="%Y-%m-%dT%H:%M",
        validators=[validators.DataRequired()],
    )
    end_date = DateTimeLocalField(
        "End date & time",
        format="%Y-%m-%dT%H:%M",
        validators=[validators.DataRequired()],
    )
    local_time_zone = StringField(
        "Local timezone", validators=[validators.DataRequired()]
    )
    status = SelectField(
        "Status",
        description="Please choose a status from the list",
        validators=[validators.DataRequired()],
    )

    def save(self):
        e = EventModel(
            name=self.name.data,
            description=self.description.data,
            location=self.location.data,
            ics_file_location=self.ics_file_location.data,
            num_seats=self.num_seats.data,
            start_date=self.start_date.data,
            end_date=self.end_date.data,
            local_time_zone=self.local_time_zone.data,
            status=self.status.data,
        )
        e.save()
        return e


class EventUpdateForm(EventForm):
    uid = HiddenField(
        "Event ID",
        description="Unique system generated ID for the event",
        validators=[validators.UUID()],
    )

    def save(self):
        e = EventModel.get(self.uid.data)
        e.name = self.name.data
        e.description = self.description.data
        e.location = self.location.data
        e.ics_file_location = self.ics_file_location.data
        e.num_seats = self.num_seats.data
        e.start_date = self.start_date.data
        e.end_date = self.end_date.data
        e.local_time_zone = self.local_time_zone.data
        e.status = self.status.data
        e.save()
        return e


class RegistrationForm(FlaskForm):
    event = SelectField(
        "Please choose an event",
        description="Click the box above to choose an event",
        validators=[validators.DataRequired(), validators.UUID()],
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

    def validate_github_username(form, field):
        if "@" in field.data:
            raise validators.ValidationError(
                "Please enter your GitHub username, not an email address"
            )

    def validate_corp_email(form, field):
        if len(
            list(
                RegistrationModel.scan(
                    (RegistrationModel.corp_email == field.data)
                    & (RegistrationModel.status != "cancelled")
                    & (RegistrationModel.event_uid == form.event.data),
                    attributes_to_get="corp_email",
                )
            )
        ):
            raise validators.ValidationError(
                "Your email address has already registered for this event. Check your confirmation email to find the link to edit."
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


class RegistrationEditForm(RegistrationForm):
    event = SelectField(
        "You cannot update event. Instead, return to the registration view and cancel registration. Then, re-register for the new event.",
        description="You cannot edit event. Instead, return to the registration view and cancel registration. Then, re-register for the new event.",
        validators=[Optional()],
    )
    uid = StringField(
        "Registration ID",
        description="Unique system generated ID",
    )

    def validate_corp_email(form, field):
        # Override dup check for edits
        pass

    def save(self):
        r = RegistrationModel.get(self.uid.data)
        r.first_name = self.first_name.data
        r.last_name = self.last_name.data
        r.corp_email = self.corp_email.data
        r.corp_sid = self.corp_sid.data
        r.personal_email = self.personal_email.data
        r.github_username = self.github_username.data
        r.save()


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


class SearchForm(FlaskForm):
    event = SelectField(
        "Please choose an event to find your registration",
        description="Click the box above to choose an event",
        validators=[validators.UUID()],
    )

    corp_email = EmailField(
        "Corporate email",
        description="Must be a valid @wellsfargo.com address",
        validators=[
            validators.DataRequired(),
            validators.Regexp(r"^.*@wellsfargo.com$"),
        ],
    )

    def save(self):
        ri = RegistrationModel.scan(
            (RegistrationModel.corp_email == self.corp_email.data)
            & (RegistrationModel.event_uid == self.event.data)
            & (RegistrationModel.status != "cancelled")
        )
        r = next(ri, None)
        return r
