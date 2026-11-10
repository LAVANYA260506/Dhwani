"""
Application endpoints (all under /api).

    POST  /applications              start an application (returns session token)
    GET   /applications/me           current state of the caller's application
    GET   /applications/me/resume    restore a session (state + field status + next field)
    GET   /applications/me/events    the application's event trail
    PATCH /applications/me/language  change the language
    PUT   /applications/me/fields    save one answer
    POST  /applications/me/confirm   confirm a field / resolve a conflict

"me" means the application that belongs to the session token in the
Authorization header.
"""

from fastapi import APIRouter, Depends, Query,Response

from app.api.deps import get_application_service, get_current_application
from app.models import Application
from app.schemas.application import (
    ApplicationCreate,
    ApplicationCreated,
    ApplicationRead,
    FieldConfirm,
    FieldUpdate,
    FieldUpdateResult,
    LanguageUpdate,
)
from app.schemas.events import EventList
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationCreated, status_code=201)
def create_application(
    payload: ApplicationCreate,
    service: ApplicationService = Depends(get_application_service),
):
    return service.create_application(payload)


@router.get("/me", response_model=ApplicationRead)
def read_my_application(
    application: Application = Depends(get_current_application),
    service: ApplicationService = Depends(get_application_service),
):
    return service.get_state(application)


@router.get("/me/resume", response_model=ApplicationRead)
def resume_my_application(
    application: Application = Depends(get_current_application),
    service: ApplicationService = Depends(get_application_service),
):
    return service.resume(application)


@router.get("/me/events", response_model=EventList)
def read_my_events(
    limit: int = Query(50, ge=1, le=200),
    after_id: int | None = Query(None, ge=0),
    application: Application = Depends(get_current_application),
    service: ApplicationService = Depends(get_application_service),
):
    return service.list_events(application, limit=limit, after_id=after_id)


@router.patch("/me/language", response_model=ApplicationRead)
def change_language(
    payload: LanguageUpdate,
    application: Application = Depends(get_current_application),
    service: ApplicationService = Depends(get_application_service),
):
    return service.update_language(application, payload.language)


@router.put("/me/fields", response_model=FieldUpdateResult)
def save_field(
    payload: FieldUpdate,
    application: Application = Depends(get_current_application),
    service: ApplicationService = Depends(get_application_service),
):
    return service.update_field(application, payload)


@router.post("/me/confirm", response_model=FieldUpdateResult)
def confirm_field(
    payload: FieldConfirm,
    application: Application = Depends(get_current_application),
    service: ApplicationService = Depends(get_application_service),
):
    return service.confirm_field(application, payload)

@router.delete("/me", status_code=204, response_class=Response)
def delete_my_application(
    application: Application = Depends(get_current_application),
    service: ApplicationService = Depends(get_application_service),
):
    service.delete_application(application)