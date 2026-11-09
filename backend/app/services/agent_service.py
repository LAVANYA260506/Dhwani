"""
Agent service: handles one conversational turn.

    response = AgentService(db).turn(application, "my PAN is ABCPE1234F", source="voice")

The language model only works out what the applicant meant (extraction.py).
Everything after that is ordinary software:

    1. Each proposed value is checked by the validation engine (dry run).
    2. Voice answers that are critical (name, date of birth, PAN, Aadhaar,
       mobile, email, register number, loan amount) are read back first, and
       so is any change to a value that is already saved. Nothing is saved
       until the applicant says yes.
    3. Saving goes through ApplicationService.update_field, the same path the
       form uses, so validation and the event trail always apply.
    4. Replies come from fixed Kannada and English templates, never from the
       model, so the assistant cannot invent an answer.

A pending read-back is stored in the conversation as a TOOL message, so it
survives a page refresh.
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_engine.agent.extraction import extract
from ai_engine.intelligence import bank_info
from ai_engine.voice.language_handler import normalize_transcript, parse_yes_no, resolve_language,romanize_if_kannada
from ai_engine.voice.text_to_speech import spell_out
from app.core.exceptions import NotFoundError
from app.models import (
    Application,
    ApplicationStatus,
    ConversationMessage,
    MessageChannel,
    MessageRole,
)
from app.schemas.agent import AgentField, AgentRejection, AgentTurnResponse
from app.schemas.application import FieldUpdate
from app.schemas.form import FieldHelp
from app.services import validation_service
from app.services.application_service import ApplicationService
from app.services.form_service import get_field_help
from shared.constants import fields as F

logger = logging.getLogger("dhwani.agent")

PENDING = "pending_confirmation"
RESOLVED = "confirmation_resolved"

# Values read back before saving (voice answers only)
CRITICAL_TYPES = {"phone", "pan", "aadhaar", "email", "date","text","textarea"}
CRITICAL_IDS = {"full_name", "register_number", "loan_amount_requested"}
SPELLED_TYPES = {"phone", "pan", "aadhaar", "pincode"}
SPELLED_IDS = {"register_number"}

_FIELD_ORDER = {field_id: i for i, field_id in enumerate(F.all_field_ids())}

TEXT: dict[str, dict[str, str]] = {
    "saved": {"en": "Saved: {items}.", "kn": "ಉಳಿಸಲಾಗಿದೆ: {items}."},
    "confirm": {
        "en": "I heard {items}. Is that correct?",
        "kn": "ನಾನು ಕೇಳಿದ್ದು {items}. ಇದು ಸರಿಯೇ?",
    },
    "retry": {
        "en": "Okay, let's try again. Please tell me: {labels}.",
        "kn": "ಸರಿ, ಮತ್ತೊಮ್ಮೆ ಪ್ರಯತ್ನಿಸೋಣ. ದಯವಿಟ್ಟು ತಿಳಿಸಿ: {labels}.",
    },
    "ask": {"en": "Please tell me: {label}.", "kn": "ದಯವಿಟ್ಟು ತಿಳಿಸಿ: {label}."},
    "complete": {
        "en": "All the required details are filled in. Please review your application.",
        "kn": "ಎಲ್ಲಾ ಅಗತ್ಯ ವಿವರಗಳನ್ನು ತುಂಬಲಾಗಿದೆ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಅರ್ಜಿಯನ್ನು ಪರಿಶೀಲಿಸಿ.",
    },
    "no_help": {
        "en": "I don't have help text for that field.",
        "kn": "ಆ ಕ್ಷೇತ್ರಕ್ಕೆ ನನ್ನ ಬಳಿ ಸಹಾಯ ಪಠ್ಯ ಇಲ್ಲ.",
    },
    "example": {"en": "For example: {example}.", "kn": "ಉದಾಹರಣೆಗೆ: {example}."},
    "not_understood": {
        "en": "Sorry, I did not understand that.",
        "kn": "ಕ್ಷಮಿಸಿ, ನನಗೆ ಅರ್ಥವಾಗಲಿಲ್ಲ.",
    },
    "submitted": {
        "en": "This application has already been submitted.",
        "kn": "ಈ ಅರ್ಜಿಯನ್ನು ಈಗಾಗಲೇ ಸಲ್ಲಿಸಲಾಗಿದೆ.",
    },
    "yes": {"en": "Yes", "kn": "ಹೌದು"},
    "no": {"en": "No", "kn": "ಇಲ್ಲ"},
    "rupees": {"en": "rupees", "kn": "ರೂಪಾಯಿ"},
    "percent": {"en": "percent", "kn": "ಶೇಕಡಾ"},
}


def _t(key: str, lang: str, **params: Any) -> str:
    return TEXT[key][lang].format(**params).replace("?.","?")


def _indian_grouping(number: int | float) -> str:
    """5,00,000 style grouping."""
    if isinstance(number, float) and not number.is_integer():
        whole, _, fraction = f"{number:.2f}".partition(".")
    else:
        whole, fraction = str(int(number)), ""
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return whole + (f".{fraction}" if fraction else "")


def display_value(field_id: str, value: Any, lang: str, speak: bool = False) -> str:
    """A value as the applicant should see (or hear) it."""
    ftype = F.get_field(field_id)["type"]

    if ftype == "choice":
        for option in F.get_options(field_id):
            if option["value"] == value:
                return option[lang]
    if ftype == "checkbox":
        return _t("yes" if value else "no", lang)
    if ftype == "date" and isinstance(value, str):
        try:
            return date.fromisoformat(value).strftime("%d %B %Y").lstrip("0")
        except ValueError:
            return str(value)
    if ftype in SPELLED_TYPES or field_id in SPELLED_IDS:
        if speak:
            return spell_out(value)
        if ftype == "aadhaar" and isinstance(value, str) and len(value) == 12:
            return f"{value[:4]} {value[4:8]} {value[8:]}"
        return str(value)
    if ftype == "email" and speak:
        return str(value).replace("@", " at ").replace(".", " dot ")
    if ftype == "currency" and isinstance(value, (int, float)):
        amount = _indian_grouping(value)
        return f"{amount} {_t('rupees', lang)}" if speak else f"\u20b9{amount}"
    if ftype == "percentage" and isinstance(value, (int, float)):
        return f"{value} {_t('percent', lang)}" if speak else f"{value}%"
    return str(value)


@dataclass
class _Turn:
    intent: str = "other"
    understood_by: str = "none"
    saved: list[AgentField] = field(default_factory=list)
    pending: list[AgentField] = field(default_factory=list)
    rejected: list[AgentRejection] = field(default_factory=list)
    help: FieldHelp | None = None
    help_missing: bool = False
    retry_labels: list[str] = field(default_factory=list)
    not_understood: bool = False
    submitted: bool = False
    info_text: str | None = None

class AgentService:
    def __init__(self, db: Session):
        self.db = db
        self.applications = ApplicationService(db)

    # -----------------------------------------------------------------
    # The turn
    # -----------------------------------------------------------------
    def turn(self, application: Application, text: str, source: str = "text") -> AgentTurnResponse:
        lang = resolve_language(application.language)
        channel = MessageChannel.VOICE if source == "voice" else MessageChannel.TEXT
        text = " ".join(text.split())
        turn = _Turn()

        self._log(application, MessageRole.APPLICANT, channel, text, lang,
                  field_id=application.current_field)

        if application.status == ApplicationStatus.SUBMITTED:
            turn.submitted = True
        else:
            pending = self._load_pending(application)
            handled = False
            if pending:
                answer = parse_yes_no(text)
                if answer is True:
                    self._resolve_pending(application, lang)
                    turn.intent = "confirm"
                    self._commit(application, pending["fields"], pending.get("source", source), lang, turn)
                    handled = True
                elif answer is False:
                    self._resolve_pending(application, lang)
                    turn.intent = "reject"
                    turn.retry_labels = [F.get_label(f, lang) for f in pending["fields"]]
                    handled = True
                else:
                    # Neither yes nor no: treat it as a fresh answer
                    self._resolve_pending(application, lang)
            if not handled:
                self._understand(application, text, source, lang, turn)

        reply = self._compose(application, lang, turn, speak=False)
        speech = self._compose(application, lang, turn, speak=True)
        self._log(application, MessageRole.ASSISTANT, channel, reply, lang,
                  field_id=application.current_field)
        self.db.commit()

        return AgentTurnResponse(
            reply=reply,
            speech=speech,
            intent=turn.intent,
            understood_by=turn.understood_by,  # type: ignore[arg-type]
            saved=turn.saved,
            pending_confirmation=turn.pending,
            rejected=turn.rejected,
            help=turn.help,
            next_field=application.current_field,
            application=self.applications.get_state(application),
        )

    # -----------------------------------------------------------------
    # Understanding
    # -----------------------------------------------------------------
    def _understand(self, application: Application, text: str, source: str, lang: str, turn: _Turn) -> None:
        extraction = extract(
            normalize_transcript(text), lang, application.current_field, dict(application.values)
        )
        turn.intent = extraction.intent
        turn.understood_by = extraction.source

        if extraction.intent in ("question","repeat"):
            self._answer_question(extraction.question_field or application.current_field, lang, turn)
        elif extraction.intent == "answer" and extraction.fields:
            self._handle_answer(application, extraction.fields, source, lang, turn)
        elif extraction.intent == "info":
            turn.info_text = bank_info.answer(
                extraction.info_topic, dict(application.values), lang
            )
        else:
            turn.not_understood = True

    def _answer_question(self, field_id: str | None, lang: str, turn: _Turn) -> None:
        if not field_id:
            turn.help_missing = True
            return
        try:
            turn.help = get_field_help(field_id, lang)
        except NotFoundError:
            turn.help_missing = True

    def _handle_answer(
        self, application: Application, proposed: dict[str, Any], source: str, lang: str, turn: _Turn
    ) -> None:
        saved_values = dict(application.values)
        merged = dict(saved_values)
        valid: dict[str, Any] = {}
        needs_confirmation = False

        for field_id, raw in sorted(proposed.items(), key=lambda kv: _FIELD_ORDER.get(kv[0], 9999)):
            # Names, places and institutions are stored in English letters,
            # whatever the speech recogniser or the model returned
            if isinstance(raw, str) and F.get_field(field_id)["type"] == "text":
                raw = romanize_if_kannada(raw)
            clean, issues = validation_service.validate_field(field_id, raw, merged, lang)
            if issues:
                turn.rejected.append(
                    AgentRejection(field_id=field_id, label=F.get_label(field_id, lang), issues=issues)
                )
                continue

            existing = saved_values.get(field_id)
            if F.is_answered(field_id, existing):
                if existing == clean:
                    continue  # already saved with this value
                needs_confirmation = True  # a change: never overwrite silently
            if source == "voice" and self._is_critical(field_id):
                needs_confirmation = True

            valid[field_id] = clean
            merged[field_id] = clean

        if not valid:
            return

        if needs_confirmation:
            turn.pending = [self._agent_field(f, v, lang) for f, v in valid.items()]
            self._log(
                application, MessageRole.TOOL, MessageChannel.SYSTEM,
                "Waiting for the applicant to confirm.", lang,
                tool_name=PENDING, tool_input={"fields": valid, "source": source},
            )
        else:
            self._commit(application, valid, source, lang, turn)

    # -----------------------------------------------------------------
    # Saving (always through the normal save path)
    # -----------------------------------------------------------------
    def _commit(
        self, application: Application, values: dict[str, Any], source: str, lang: str, turn: _Turn
    ) -> None:
        save_source = "voice" if source == "voice" else "text"
        for field_id, value in sorted(values.items(), key=lambda kv: _FIELD_ORDER.get(kv[0], 9999)):
            result = self.applications.update_field(
                application, FieldUpdate(field_id=field_id, value=value, source=save_source)
            )
            self._log(
                application, MessageRole.TOOL, MessageChannel.SYSTEM,
                f"update_field {field_id}", lang, field_id=field_id,
                tool_name="update_field", tool_input={"field_id": field_id, "value": value},
                tool_result={"accepted": result.accepted},
            )
            if result.accepted:
                turn.saved.append(self._agent_field(field_id, result.value, lang))
            else:
                turn.rejected.append(
                    AgentRejection(field_id=field_id, label=F.get_label(field_id, lang), issues=result.issues)
                )

    @staticmethod
    def _is_critical(field_id: str) -> bool:
        return field_id in CRITICAL_IDS or F.get_field(field_id)["type"] in CRITICAL_TYPES

    @staticmethod
    def _agent_field(field_id: str, value: Any, lang: str) -> AgentField:
        return AgentField(field_id=field_id, label=F.get_label(field_id, lang), value=value)

    # -----------------------------------------------------------------
    # Replies (fixed templates, no model involved)
    # -----------------------------------------------------------------
    def _items(self, fields: list[AgentField], lang: str, speak: bool) -> str:
        return "; ".join(
            f"{item.label}: {display_value(item.field_id, item.value, lang, speak)}" for item in fields
        )

    def _compose(self, application: Application, lang: str, turn: _Turn, speak: bool) -> str:
        if turn.submitted:
            return _t("submitted", lang)

        parts: list[str] = []

        if turn.help is not None:
            parts.append(turn.help.explanation)
            if turn.help.example:
                parts.append(_t("example", lang, example=turn.help.example))
        elif turn.help_missing:
            parts.append(_t("no_help", lang))
        if turn.info_text:
            parts.append(turn.info_text)
        if turn.not_understood:
            parts.append(_t("not_understood", lang))

        for rejection in turn.rejected:
            issue = rejection.issues[0]
            line = f"{rejection.label}: {issue.message}"
            if issue.hint:
                line += f" {issue.hint}"
            if not line.endswith((".", "?", "!")):
                line += "."
            parts.append(line)

        if turn.pending:
            parts.append(_t("confirm", lang, items=self._items(turn.pending, lang, speak)))
            return " ".join(parts)

        if turn.retry_labels:
            parts.append(_t("retry", lang, labels=", ".join(turn.retry_labels)))
            return " ".join(parts)

        if turn.saved:
            parts.append(_t("saved", lang, items=self._items(turn.saved, lang, speak)))

        # Re-ask what failed; otherwise move on to the next field
        ask_field = turn.rejected[0].field_id if turn.rejected else application.current_field
        if ask_field:
            parts.append(_t("ask", lang, label=F.get_label(ask_field, lang)))
        elif application.status == ApplicationStatus.READY_FOR_REVIEW:
            parts.append(_t("complete", lang))
        return " ".join(parts)

    # -----------------------------------------------------------------
    # Conversation storage
    # -----------------------------------------------------------------
    def _log(
        self,
        application: Application,
        role: MessageRole,
        channel: MessageChannel,
        content: str,
        lang: str,
        *,
        field_id: str | None = None,
        tool_name: str | None = None,
        tool_input: dict[str, Any] | None = None,
        tool_result: dict[str, Any] | None = None,
    ) -> None:
        self.db.add(
            ConversationMessage(
                application_id=application.id, role=role, channel=channel, language=lang,
                content=content, field_id=field_id, tool_name=tool_name,
                tool_input=tool_input, tool_result=tool_result,
            )
        )

    def _load_pending(self, application: Application) -> dict[str, Any] | None:
        """The read-back waiting for yes/no, if the latest such marker is one."""
        statement = (
            select(ConversationMessage)
            .where(
                ConversationMessage.application_id == application.id,
                ConversationMessage.role == MessageRole.TOOL,
                ConversationMessage.tool_name.in_([PENDING, RESOLVED]),
            )
            .order_by(ConversationMessage.id.desc())
            .limit(1)
        )
        latest = self.db.execute(statement).scalar_one_or_none()
        if latest is not None and latest.tool_name == PENDING and latest.tool_input:
            return latest.tool_input
        return None

    def _resolve_pending(self, application: Application, lang: str) -> None:
        self._log(
            application, MessageRole.TOOL, MessageChannel.SYSTEM,
            "Confirmation answered.", lang, tool_name=RESOLVED,
        )
        self.db.flush()