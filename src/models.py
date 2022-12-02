import os
import uuid
from typing import Any
from pynamodb.models import Model
from pynamodb.constants import (
    STREAM_NEW_AND_OLD_IMAGE,
    PAY_PER_REQUEST_BILLING_MODE,
    STRING,
)
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    UTCDateTimeAttribute,
    BooleanAttribute,
    Attribute,
    ListAttribute,
)
from constants import REGISTRATION_STATES


#########################
# Custom table attributes
#########################


class UUIDAttribute(Attribute[uuid.UUID]):
    """
    PynamoDB attribute to for UUIDs. These are backed by DynamoDB unicode (`S`) types.
    """

    attr_type = STRING

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
        region = os.environ.get("AWS_REGION", "us-east-1")
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
    gh_team = UnicodeAttribute(null=True)


class StateTransitionError(Exception):
    pass


class RegistrationModel(Model):
    class Meta:
        table_name = "levelup-registration"
        region = os.environ.get("AWS_REGION", "us-east-1")
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
    comms_status = UnicodeAttribute(null=True)
    gh_status = UnicodeAttribute(null=True)
    six_week_comms = BooleanAttribute(null=True)
    two_week_comms = BooleanAttribute(null=True)
    next_week_comms = BooleanAttribute(null=True)
    close_comms = BooleanAttribute(null=True)

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
        region = os.environ.get("AWS_REGION", "us-east-1")
        stream_view_type = STREAM_NEW_AND_OLD_IMAGE
        billing_mode = PAY_PER_REQUEST_BILLING_MODE

    team_number = NumberAttribute(hash_key=True)
    name = UnicodeAttribute()
    num_members = NumberAttribute()
    tech_stack = UnicodeAttribute()
    repo_url = UnicodeAttribute(null=True)
    env_urls = ListAttribute(null=True)


def create_all_tables():
    if not EventModel.exists():
        EventModel.create_table(wait=True)

    if not RegistrationModel.exists():
        RegistrationModel.create_table(wait=True)

    if not TeamModel.exists():
        TeamModel.create_table(wait=True)
