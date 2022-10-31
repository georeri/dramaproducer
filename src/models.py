import uuid
from django.db import models


class Event(models.Model):
    STATUSES = [
        ("open", "Registration Open"),
        ("closed", "Registration Closed"),
        ("complete", "Event Completed"),
        ("cancelled", "Event Cancelled"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30)
    description = models.TextField()
    min_seats = models.IntegerField(default=50)
    max_seats = models.IntegerField(default=150)
    location = models.CharField(max_length=256)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=30, choices=STATUSES, default="open")
    created = models.DateTimeField(auto_now_add=True, editable=False)
    last_updated = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name


class Participant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fist_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    corp_email = models.EmailField(unique=True)
    corp_id = models.CharField(max_length=7)
    personal_email = models.EmailField(blank=True)
    github_user_id = models.CharField(max_length=50, blank=True)
    registered_events = models.ManyToManyField(Event, through="Registration")

    def __str__(self):
        return f"{self.last_name}, {self.fist_name}"


class Registration(models.Model):
    STATUSES = [
        ("registered", "Registered"),
        ("attended", "Attended"),
        ("no-show", "No Show"),
        ("cancelled", "Cancelled"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    status = models.CharField(max_length=30, choices=STATUSES, default="registered")
    reference_id = models.CharField(max_length=256, blank=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return f"Registration ID: {self.id}"
