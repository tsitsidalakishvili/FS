from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OutputModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class PersonCreate(InputModel):
    email: str = Field(min_length=3, max_length=320)
    firstName: str | None = None
    lastName: str | None = None
    phone: str | None = None


class PersonPatch(InputModel):
    firstName: str | None = None
    lastName: str | None = None
    phone: str | None = None
    status: Literal["ACTIVE", "ARCHIVED"] | None = None


class PersonOut(OutputModel):
    personId: str
    email: str
    firstName: str | None = None
    lastName: str | None = None
    phone: str | None = None
    status: str
    createdAt: datetime
    updatedAt: datetime


class TaskCreate(InputModel):
    personId: str
    title: str = Field(min_length=1, max_length=200)
    ownerId: str = Field(min_length=1, max_length=120)
    description: str | None = None
    dueDate: str | None = None


class TaskStatusPatch(InputModel):
    status: Literal["Open", "In Progress", "Done", "Cancelled"]


class TaskOut(OutputModel):
    taskId: str
    personId: str
    title: str
    ownerId: str
    status: str
    description: str | None = None
    dueDate: str | None = None
    createdAt: datetime
    updatedAt: datetime


class EventCreate(InputModel):
    eventKey: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    published: bool = False


class EventOut(OutputModel):
    eventId: str
    eventKey: str
    name: str
    published: bool
    createdAt: datetime
    updatedAt: datetime


class DeepLinkCreate(InputModel):
    subjectPersonId: str
    expiresInHours: int = Field(default=24, ge=1, le=720)


class DeepLinkOut(OutputModel):
    token: str
    expiresAt: datetime


class PublicRegistrationCreate(InputModel):
    token: str = Field(min_length=8)
    status: Literal["Registered", "Attended", "Cancelled", "No Show"] = "Registered"
    guestCount: int | None = Field(default=None, ge=0, le=20)
    accessibilityNeeds: str | None = None
    consentVersion: str | None = None
    notes: str | None = None


class PublicRegistrationOut(OutputModel):
    registrationId: str
    eventId: str
    status: str
    createdAt: datetime


class EventRegistrationOut(OutputModel):
    registrationId: str
    personId: str
    status: str
    createdAt: datetime

