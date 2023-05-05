import os
import uuid
from dateutil import tz
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
from constants import AWS_DEFAULT_REGION
# AWS_DEFAULT_REGION = 'us-east-1'
DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT")


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


class ProductionModel(Model):
    class Meta:
        table_name = "dp-production"
        region = AWS_DEFAULT_REGION
        billing_mode = PAY_PER_REQUEST_BILLING_MODE
        if DYNAMODB_ENDPOINT:
            host = DYNAMODB_ENDPOINT

    uid = UUIDAttribute(hash_key=True, default_for_new=uuid.uuid4)
    name = UnicodeAttribute()
    description = UnicodeAttribute()
    status = UnicodeAttribute(default="open")
    
    def __str__(self):
        return str(self.uid)
    
class AuditionModel(Model):
    class Meta:
        table_name = "dp-audition"
        region = AWS_DEFAULT_REGION
        billing_mode = PAY_PER_REQUEST_BILLING_MODE
        if DYNAMODB_ENDPOINT:
            host = DYNAMODB_ENDPOINT

    uid = UUIDAttribute(hash_key=True, default_for_new=uuid.uuid4)
    name = UnicodeAttribute()
    production_uid = UUIDAttribute()
    email = UnicodeAttribute()
    phone_number = UnicodeAttribute()
    parent_email = UnicodeAttribute()
    parent_phone_number = UnicodeAttribute()
    age = NumberAttribute()
    vocal_range = UnicodeAttribute()
    resume = UnicodeAttribute()
    status = UnicodeAttribute(default="new")
    
    def __str__(self):
        return str(self.uid)

def create_all_tables():
    if not ProductionModel.exists():
        ProductionModel.create_table(wait=True)
    if not AuditionModel.exists():
        AuditionModel.create_table(wait=True)

if __name__ == "__main__":
    create_all_tables()
