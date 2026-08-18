from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# --- Patient ---
class PatientCreate(BaseModel):
    name: str
    notes: Optional[str] = None


class PatientOut(BaseModel):
    id: int
    name: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Medication ---
class MedicationCreate(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    status: str = "active"  # active / past / discontinued
    prescribed_date: Optional[str] = None  # e.g. "2024-01-15" — when it was actually prescribed
    notes: Optional[str] = None


class MedicationOut(MedicationCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Allergy ---
class AllergyCreate(BaseModel):
    substance: str
    reaction: Optional[str] = None
    severity: Optional[str] = None
    identified_date: Optional[str] = None  # e.g. "2019-03-10" — when the allergy was identified


class AllergyOut(AllergyCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Condition ---
class ConditionCreate(BaseModel):
    name: str
    status: Optional[str] = None
    notes: Optional[str] = None
    diagnosed_date: Optional[str] = None  # e.g. "2021-11-02" — when diagnosed


class ConditionOut(ConditionCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Message / Chat ---
class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    stream: bool = False


class ChatResponse(BaseModel):
    reply: str
    model: str
    disclaimer: str = (
        "This information is general and educational, not a medical "
        "diagnosis. Consult a licensed healthcare professional for advice "
        "specific to your situation. In an emergency, contact local "
        "emergency services immediately."
    )


class PatientSummary(BaseModel):
    patient: PatientOut
    medications: List[MedicationOut]
    allergies: List[AllergyOut]
    conditions: List[ConditionOut]
    message_count: int
