from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from src.api.core.audit import write_audit_log
from src.api.core.auth import get_current_user, require_roles, decode_token, oauth2_scheme
from src.api.core.db import get_db
from src.api.models import Resident, ResidentPrivacyPreferences, User
from src.api.schemas import (
    ResidentCreate,
    ResidentDirectoryItem,
    ResidentProfileOut,
    ResidentUpdate,
    ResidentPrivacyPreferencesOut,
)

router = APIRouter(prefix="/residents", tags=["Residents"])


def _is_admin(token: str) -> bool:
    claims = decode_token(token)
    roles = claims.get("roles") or []
    return "admin" in roles


def _directory_item_for(resident: Resident, *, admin: bool) -> Optional[ResidentDirectoryItem]:
    prefs = resident.privacy_preferences
    if prefs is None:
        prefs = ResidentPrivacyPreferences(resident_id=resident.id)

    if (not admin) and prefs.hide_profile_from_directory:
        return None

    display_first = resident.first_name
    if (not admin) and prefs.show_preferred_name and resident.preferred_name:
        display_first = resident.preferred_name

    email = resident.email if (admin or not prefs.hide_email) else None
    phone = resident.phone if (admin or not prefs.hide_phone) else None

    # For directory, treat building/floor/unit_number as address-like fields for hide_address.
    building = resident.building if (admin or not prefs.hide_address) else None
    floor = resident.floor if (admin or not prefs.hide_address) else None
    unit_number = resident.unit_number if (admin or not prefs.hide_address) else None

    return ResidentDirectoryItem(
        id=resident.id,
        display_name=f"{display_first} {resident.last_name}",
        unit_identifier=resident.unit_identifier,
        building=building,
        floor=floor,
        unit_number=unit_number,
        email=email,
        phone=phone,
    )


def _profile_for(resident: Resident, *, admin: bool) -> ResidentProfileOut:
    prefs = resident.privacy_preferences
    if prefs is None:
        prefs = ResidentPrivacyPreferences(resident_id=resident.id)

    first_name = resident.first_name
    if (not admin) and prefs.show_preferred_name and resident.preferred_name:
        first_name = resident.preferred_name

    email = resident.email if (admin or not prefs.hide_email) else None
    phone = resident.phone if (admin or not prefs.hide_phone) else None

    # Address fields hidden if hide_address (for non-admin)
    def addr(val: Optional[str]) -> Optional[str]:
        return val if (admin or not prefs.hide_address) else None

    # Notes should only be visible to admins
    notes = resident.notes if admin else None

    return ResidentProfileOut(
        id=resident.id,
        first_name=first_name,
        last_name=resident.last_name,
        preferred_name=resident.preferred_name,
        unit_identifier=resident.unit_identifier,
        email=email,
        phone=phone,
        building=addr(resident.building),
        floor=addr(resident.floor),
        unit_number=addr(resident.unit_number),
        address_line1=addr(resident.address_line1),
        address_line2=addr(resident.address_line2),
        city=addr(resident.city),
        state=addr(resident.state),
        postal_code=addr(resident.postal_code),
        country=addr(resident.country),
        notes=notes,
        is_active=resident.is_active,
        privacy_preferences=ResidentPrivacyPreferencesOut(
            hide_email=prefs.hide_email,
            hide_phone=prefs.hide_phone,
            hide_address=prefs.hide_address,
            hide_profile_from_directory=prefs.hide_profile_from_directory,
            show_preferred_name=prefs.show_preferred_name,
        ),
        created_at=resident.created_at,  # SQLAlchemy will provide datetime-like; Pydantic handles it
        updated_at=resident.updated_at,
    )


@router.get(
    "",
    response_model=List[ResidentDirectoryItem],
    summary="List residents",
    description="List/search/filter residents for the directory. Privacy preferences are enforced for non-admin users.",
    operation_id="residents_list",
)
# PUBLIC_INTERFACE
def list_residents(
    request: Request,
    q: Optional[str] = Query(default=None, description="Search query (matches name, unit_identifier, email)."),
    building: Optional[str] = Query(default=None, description="Filter by building."),
    is_active: Optional[bool] = Query(default=True, description="Filter active residents (default true)."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
) -> List[ResidentDirectoryItem]:
    """List residents with privacy enforcement."""
    admin = _is_admin(token)

    query = db.query(Resident).options(joinedload(Resident.privacy_preferences))

    filters = []
    if is_active is not None:
        filters.append(Resident.is_active == is_active)
    if building:
        filters.append(Resident.building == building)
    if q:
        q_like = f"%{q.strip()}%"
        filters.append(
            or_(
                Resident.first_name.ilike(q_like),
                Resident.last_name.ilike(q_like),
                Resident.preferred_name.ilike(q_like),
                Resident.unit_identifier.ilike(q_like),
                Resident.email.ilike(q_like),
            )
        )

    if filters:
        query = query.filter(and_(*filters))

    residents = query.order_by(Resident.last_name.asc(), Resident.first_name.asc()).limit(200).all()

    items: List[ResidentDirectoryItem] = []
    for r in residents:
        item = _directory_item_for(r, admin=admin)
        if item is not None:
            items.append(item)

    write_audit_log(
        db,
        request=request,
        actor=user,
        action="residents_list",
        entity_type="resident",
        entity_id=None,
        details={"q": q, "building": building, "is_active": is_active, "returned": len(items), "admin": admin},
    )
    return items


@router.get(
    "/{resident_id}",
    response_model=ResidentProfileOut,
    summary="Get resident profile",
    description="Get a resident profile. Privacy preferences are enforced for non-admin users.",
    operation_id="residents_get_profile",
)
# PUBLIC_INTERFACE
def get_resident_profile(
    resident_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
) -> ResidentProfileOut:
    """Get resident profile with privacy enforcement."""
    admin = _is_admin(token)

    resident = (
        db.query(Resident)
        .options(joinedload(Resident.privacy_preferences))
        .filter(Resident.id == resident_id)
        .one_or_none()
    )
    if resident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    prefs = resident.privacy_preferences
    if prefs is None:
        prefs = ResidentPrivacyPreferences(resident_id=resident.id)

    if (not admin) and prefs.hide_profile_from_directory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    out = _profile_for(resident, admin=admin)
    write_audit_log(
        db,
        request=request,
        actor=user,
        action="resident_view",
        entity_type="resident",
        entity_id=str(resident_id),
        details={"admin": admin},
    )
    return out


@router.post(
    "",
    response_model=ResidentProfileOut,
    summary="Create resident (admin)",
    description="Admin-only: create a resident profile and default privacy preferences.",
    operation_id="residents_admin_create",
)
# PUBLIC_INTERFACE
def admin_create_resident(
    payload: ResidentCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin"])),
) -> ResidentProfileOut:
    """Admin-only create resident."""
    resident = Resident(
        unit_identifier=payload.unit_identifier,
        first_name=payload.first_name,
        last_name=payload.last_name,
        preferred_name=payload.preferred_name,
        email=payload.email,
        phone=payload.phone,
        building=payload.building,
        floor=payload.floor,
        unit_number=payload.unit_number,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        country=payload.country,
        notes=payload.notes,
        is_active=payload.is_active,
        created_by=admin_user.id,
        updated_by=admin_user.id,
    )
    resident.privacy_preferences = ResidentPrivacyPreferences(resident_id=0)  # overwritten on flush

    db.add(resident)
    db.flush()  # assigns resident.id
    # Fix FK on privacy prefs
    if resident.privacy_preferences is not None:
        resident.privacy_preferences.resident_id = resident.id
        resident.privacy_preferences.updated_by = admin_user.id

    db.commit()
    db.refresh(resident)

    write_audit_log(
        db,
        request=request,
        actor=admin_user,
        action="resident_create",
        entity_type="resident",
        entity_id=str(resident.id),
        details={"unit_identifier": resident.unit_identifier},
    )

    return _profile_for(resident, admin=True)


@router.put(
    "/{resident_id}",
    response_model=ResidentProfileOut,
    summary="Update resident (admin)",
    description="Admin-only: update resident profile and/or privacy preferences.",
    operation_id="residents_admin_update",
)
# PUBLIC_INTERFACE
def admin_update_resident(
    resident_id: int,
    payload: ResidentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin"])),
) -> ResidentProfileOut:
    """Admin-only update resident."""
    resident = (
        db.query(Resident)
        .options(joinedload(Resident.privacy_preferences))
        .filter(Resident.id == resident_id)
        .one_or_none()
    )
    if resident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    # Update scalar fields
    for field in [
        "unit_identifier",
        "first_name",
        "last_name",
        "preferred_name",
        "email",
        "phone",
        "building",
        "floor",
        "unit_number",
        "address_line1",
        "address_line2",
        "city",
        "state",
        "postal_code",
        "country",
        "notes",
        "is_active",
    ]:
        val = getattr(payload, field)
        if val is not None:
            setattr(resident, field, val)

    resident.updated_by = admin_user.id

    # Ensure privacy pref row exists
    if resident.privacy_preferences is None:
        resident.privacy_preferences = ResidentPrivacyPreferences(resident_id=resident.id)

    if payload.privacy_preferences is not None:
        pp = payload.privacy_preferences
        for f in ["hide_email", "hide_phone", "hide_address", "hide_profile_from_directory", "show_preferred_name"]:
            v = getattr(pp, f)
            if v is not None:
                setattr(resident.privacy_preferences, f, v)
        resident.privacy_preferences.updated_by = admin_user.id

    db.commit()
    db.refresh(resident)

    write_audit_log(
        db,
        request=request,
        actor=admin_user,
        action="resident_update",
        entity_type="resident",
        entity_id=str(resident_id),
        details={"fields_updated": [k for k, v in payload.model_dump(exclude_none=True).items() if k != "privacy_preferences"]},
    )
    return _profile_for(resident, admin=True)


@router.delete(
    "/{resident_id}",
    status_code=204,
    summary="Delete resident (admin)",
    description="Admin-only: delete resident (cascades privacy preferences).",
    operation_id="residents_admin_delete",
)
# PUBLIC_INTERFACE
def admin_delete_resident(
    resident_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin"])),
) -> Response:
    """Admin-only delete resident.

    Notes:
        FastAPI disallows response bodies for HTTP 204. Return an explicit empty Response.
    """
    resident = db.query(Resident).filter(Resident.id == resident_id).one_or_none()
    if resident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    db.delete(resident)
    db.commit()

    write_audit_log(
        db,
        request=request,
        actor=admin_user,
        action="resident_delete",
        entity_type="resident",
        entity_id=str(resident_id),
        details={},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
