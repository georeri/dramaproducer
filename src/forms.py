from datetime import datetime, timezone
from dateutil import tz
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

from models import ProductionModel

#########################
# Form definitions
#########################


class ProductionForm(FlaskForm):
    name = StringField("Production name", validators=[validators.DataRequired()])
    description = TextAreaField("Description", validators=[validators.DataRequired()])
    status = SelectField(
        "Status",
        description="Please choose a status from the list",
        validators=[validators.DataRequired()],
    )

    def save(self):
        p = ProductionModel(
            name=self.name.data,
            description=self.description.data,
            status=self.status.data,
        )
        p.save()
        return p


class ProductionUpdateForm(ProductionForm):
    uid = HiddenField(
        "Production ID",
        description="Unique system generated ID for the production",
        validators=[validators.UUID()],
    )

    def save(self):
        p = ProductionModel.get(self.uid.data)
        p.name = self.name.data
        p.description = self.description.data
        p.status = self.status.data
        p.save()
        return p
