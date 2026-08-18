"""
Data model.

Deliberate design choice: medications / allergies / conditions are
separate structured tables edited only through explicit CRUD endpoints —
never written automatically from freeform chat. The model reads this
data to personalize its answers; it never writes to it. That keeps a
hallucinated "the patient mentioned they're allergic to X" from silently
becoming a stored fact.

Message is the raw chat log, used for conversational continuity
("what did I ask you earlier") separately from the structured facts.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    notes = Column(Text, nullable=True)  # free-text general notes, clinician-entered
    created_at = Column(DateTime, default=utcnow)

    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    allergies = relationship("Allergy", back_populates="patient", cascade="all, delete-orphan")
    conditions = relationship("Condition", back_populates="patient", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="patient", cascade="all, delete-orphan")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=True)
    frequency = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")  # active / past / discontinued
    prescribed_date = Column(String, nullable=True)  # user-entered date, e.g. "2024-01-15" — when it was actually prescribed
    created_at = Column(DateTime, default=utcnow)  # when this record was added to the system
    notes = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="medications")


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    substance = Column(String, nullable=False)
    reaction = Column(String, nullable=True)
    severity = Column(String, nullable=True)  # e.g. mild / moderate / severe
    identified_date = Column(String, nullable=True)  # user-entered date, e.g. "2019-03-10" — when the allergy was identified
    created_at = Column(DateTime, default=utcnow)  # when this record was added to the system

    patient = relationship("Patient", back_populates="allergies")


class Condition(Base):
    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, nullable=True)  # e.g. active / resolved / chronic
    notes = Column(Text, nullable=True)
    diagnosed_date = Column(String, nullable=True)  # user-entered date, e.g. "2021-11-02" — when diagnosed
    created_at = Column(DateTime, default=utcnow)  # when this record was added to the system

    patient = relationship("Patient", back_populates="conditions")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    patient = relationship("Patient", back_populates="messages")
