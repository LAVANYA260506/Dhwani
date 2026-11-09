"""
Form endpoints (public, no session needed; the form is the same for everyone).

    GET /form                          full form definition (sections, fields, options)
    GET /form/fields/{field_id}/help   verified explanation of one field
"""

from fastapi import APIRouter

from app.schemas.form import FieldHelp, FormDefinition
from app.services import form_service

router = APIRouter(prefix="/form", tags=["form"])


@router.get("", response_model=FormDefinition)
def get_form():
    return form_service.get_form_definition()


@router.get("/fields/{field_id}/help", response_model=FieldHelp)
def get_field_help(field_id: str, language: str = "en"):
    return form_service.get_field_help(field_id, language)