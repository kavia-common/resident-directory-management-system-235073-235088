from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field(default="bearer", description="Token type (bearer).")
    roles: List[str] = Field(..., description="Roles granted to the user.")
    user: Dict[str, Any] = Field(..., description="Basic user profile.")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email.")
    password: str = Field(..., description="User password.")


class SignupRequest(BaseModel):
    email: str = Field(..., description="User email (must be unique).")
    password: str = Field(..., description="User password (will be hashed).")
    display_name: Optional[str] = Field(default=None, description="Optional display name.")


class ResidentPrivacyPreferencesOut(BaseModel):
    hide_email: bool = Field(..., description="If true, email is hidden from non-admin directory/profile views.")
    hide_phone: bool = Field(..., description="If true, phone is hidden from non-admin directory/profile views.")
    hide_address: bool = Field(..., description="If true, address fields are hidden from non-admin views.")
    hide_profile_from_directory: bool = Field(
        ..., description="If true, resident does not appear in directory for non-admins."
    )
    show_preferred_name: bool = Field(..., description="If true, preferred_name may be shown instead of first_name.")


class ResidentDirectoryItem(BaseModel):
    id: int = Field(..., description="Resident ID.")
    display_name: str = Field(..., description="Name shown in directory respecting privacy preferences.")
    unit_identifier: str = Field(..., description="Unit identifier.")
    building: Optional[str] = Field(default=None, description="Building (may be hidden).")
    floor: Optional[str] = Field(default=None, description="Floor (may be hidden).")
    unit_number: Optional[str] = Field(default=None, description="Unit number (may be hidden).")
    email: Optional[str] = Field(default=None, description="Email (may be hidden).")
    phone: Optional[str] = Field(default=None, description="Phone (may be hidden).")


class ResidentProfileOut(BaseModel):
    id: int = Field(..., description="Resident ID.")
    first_name: str = Field(..., description="First name (may be preferred_name for non-admin).")
    last_name: str = Field(..., description="Last name.")
    preferred_name: Optional[str] = Field(default=None, description="Preferred name.")
    unit_identifier: str = Field(..., description="Unit identifier.")
    email: Optional[str] = Field(default=None, description="Email (may be hidden).")
    phone: Optional[str] = Field(default=None, description="Phone (may be hidden).")
    building: Optional[str] = Field(default=None, description="Building (may be hidden).")
    floor: Optional[str] = Field(default=None, description="Floor (may be hidden).")
    unit_number: Optional[str] = Field(default=None, description="Unit number (may be hidden).")

    address_line1: Optional[str] = Field(default=None, description="Address line 1 (may be hidden).")
    address_line2: Optional[str] = Field(default=None, description="Address line 2 (may be hidden).")
    city: Optional[str] = Field(default=None, description="City (may be hidden).")
    state: Optional[str] = Field(default=None, description="State (may be hidden).")
    postal_code: Optional[str] = Field(default=None, description="Postal code (may be hidden).")
    country: Optional[str] = Field(default=None, description="Country (may be hidden).")

    notes: Optional[str] = Field(default=None, description="Internal notes (admin-only in practice).")
    is_active: bool = Field(..., description="Whether resident is active.")
    privacy_preferences: ResidentPrivacyPreferencesOut = Field(..., description="Privacy preferences.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Update timestamp.")


class ResidentPrivacyPreferencesUpdate(BaseModel):
    hide_email: Optional[bool] = Field(default=None, description="Hide email.")
    hide_phone: Optional[bool] = Field(default=None, description="Hide phone.")
    hide_address: Optional[bool] = Field(default=None, description="Hide address.")
    hide_profile_from_directory: Optional[bool] = Field(default=None, description="Hide profile from directory.")
    show_preferred_name: Optional[bool] = Field(default=None, description="Show preferred name.")


class ResidentCreate(BaseModel):
    unit_identifier: str = Field(..., description="Unit identifier.")
    first_name: str = Field(..., description="First name.")
    last_name: str = Field(..., description="Last name.")
    preferred_name: Optional[str] = Field(default=None, description="Preferred name.")
    email: Optional[str] = Field(default=None, description="Email.")
    phone: Optional[str] = Field(default=None, description="Phone.")
    building: Optional[str] = Field(default=None, description="Building.")
    floor: Optional[str] = Field(default=None, description="Floor.")
    unit_number: Optional[str] = Field(default=None, description="Unit number.")
    address_line1: Optional[str] = Field(default=None, description="Address line 1.")
    address_line2: Optional[str] = Field(default=None, description="Address line 2.")
    city: Optional[str] = Field(default=None, description="City.")
    state: Optional[str] = Field(default=None, description="State.")
    postal_code: Optional[str] = Field(default=None, description="Postal code.")
    country: Optional[str] = Field(default=None, description="Country.")
    notes: Optional[str] = Field(default=None, description="Internal notes.")
    is_active: bool = Field(default=True, description="Whether resident is active.")


class ResidentUpdate(BaseModel):
    unit_identifier: Optional[str] = Field(default=None, description="Unit identifier.")
    first_name: Optional[str] = Field(default=None, description="First name.")
    last_name: Optional[str] = Field(default=None, description="Last name.")
    preferred_name: Optional[str] = Field(default=None, description="Preferred name.")
    email: Optional[str] = Field(default=None, description="Email.")
    phone: Optional[str] = Field(default=None, description="Phone.")
    building: Optional[str] = Field(default=None, description="Building.")
    floor: Optional[str] = Field(default=None, description="Floor.")
    unit_number: Optional[str] = Field(default=None, description="Unit number.")
    address_line1: Optional[str] = Field(default=None, description="Address line 1.")
    address_line2: Optional[str] = Field(default=None, description="Address line 2.")
    city: Optional[str] = Field(default=None, description="City.")
    state: Optional[str] = Field(default=None, description="State.")
    postal_code: Optional[str] = Field(default=None, description="Postal code.")
    country: Optional[str] = Field(default=None, description="Country.")
    notes: Optional[str] = Field(default=None, description="Internal notes.")
    is_active: Optional[bool] = Field(default=None, description="Whether resident is active.")
    privacy_preferences: Optional[ResidentPrivacyPreferencesUpdate] = Field(
        default=None, description="Privacy preference updates."
    )
