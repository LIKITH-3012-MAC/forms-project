import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, HttpUrl

class RegistrationCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150, description="Full Name of the attendee")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., description="10-digit phone number or with +91 prefix")
    college: str = Field(..., max_length=200, description="College name")
    department: str = Field(..., max_length=120, description="Department name")
    year: str = Field(..., description="Academic year")
    roll_number: Optional[str] = Field(None, max_length=50, description="College roll number")
    upi_reference_id: str = Field(..., min_length=8, max_length=120, description="UPI/UTR transaction reference ID")
    payment_screenshot_url: Optional[str] = Field(None, description="Optional payment screenshot URL")
    confirm: bool = Field(..., description="Must confirm details are correct")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        # Match standard Indian phone numbers (+91XXXXXXXXXX or XXXXXXXXXX)
        cleaned = re.sub(r"\s+", "", v)
        if not re.match(r"^(\+91)?[6789]\d{9}$", cleaned):
            raise ValueError("Phone number must be a valid 10-digit number, optionally prefixed with +91")
        return cleaned

    @field_validator("upi_reference_id")
    @classmethod
    def clean_utr(cls, v):
        # Trim whitespace and normalize to uppercase
        cleaned = v.strip().upper()
        if len(cleaned) < 8:
            raise ValueError("UPI/UTR reference ID must be at least 8 characters long")
        return cleaned

    @field_validator("payment_screenshot_url")
    @classmethod
    def validate_screenshot_url(cls, v):
        if not v:
            return None
        # Basic URL matching if not empty
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", v):
            raise ValueError("Payment screenshot URL must be a valid HTTP or HTTPS URL")
        return v

    @field_validator("confirm")
    @classmethod
    def validate_confirm(cls, v):
        if not v:
            raise ValueError("You must confirm that the details are correct")
        return v


class RegistrationUpdate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(...)
    college: str = Field(..., max_length=200)
    department: str = Field(..., max_length=120)
    year: str = Field(...)
    roll_number: Optional[str] = Field(None, max_length=50)
    upi_reference_id: str = Field(..., min_length=8, max_length=120)
    payment_screenshot_url: Optional[str] = Field(None)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        cleaned = re.sub(r"\s+", "", v)
        if not re.match(r"^(\+91)?[6789]\d{9}$", cleaned):
            raise ValueError("Phone number must be a valid 10-digit number, optionally prefixed with +91")
        return cleaned

    @field_validator("upi_reference_id")
    @classmethod
    def clean_utr(cls, v):
        cleaned = v.strip().upper()
        if len(cleaned) < 8:
            raise ValueError("UPI/UTR reference ID must be at least 8 characters long")
        return cleaned

    @field_validator("payment_screenshot_url")
    @classmethod
    def validate_screenshot_url(cls, v):
        if not v:
            return None
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", v):
            raise ValueError("Payment screenshot URL must be a valid HTTP or HTTPS URL")
        return v


class AdminAction(BaseModel):
    admin_note: Optional[str] = None


class AdminLogin(BaseModel):
    admin_password: str

