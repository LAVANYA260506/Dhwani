// Types mirroring the backend API (backend/app/schemas/*.py)

export type Language = "en" | "kn";
export type ApplicationStatus =
  | "draft"
  | "in_progress"
  | "ready_for_review"
  | "submitted";
export type FieldValue = string | number | boolean | null;
export type AnswerSource = "voice" | "text";

export interface FieldIssue {
  code: string;
  message: string;
  hint?: string | null;
  suggested_field?: string | null;
}

export interface SectionProgress {
  section_id: string;
  answered: number;
  total: number;
}

export interface ProgressSummary {
  answered_required: number;
  total_required: number;
  percent: number;
  complete: boolean;
  sections: SectionProgress[];
}

export interface InvalidField {
  field_id: string;
  code: string;
  message: string;
  hint?: string | null;
}

export interface FieldStatus {
  completed: string[];
  pending: string[];
  invalid: InvalidField[];
}

export interface ApplicationRead {
  id: string;
  status: ApplicationStatus;
  language: Language;
  values: Record<string, FieldValue>;
  confirmed_fields: string[];
  field_sources: Record<string, string>;
  current_field: string | null;
  consent_given: boolean;
  reference_id: string | null;
  created_at: string;
  updated_at: string;
  progress: ProgressSummary | null;
  field_status: FieldStatus | null;
}

export interface ApplicationCreated {
  application_id: string;
  session_token: string;
  status: ApplicationStatus;
  language: Language;
}

export interface FieldUpdateResult {
  field_id: string;
  accepted: boolean;
  value: FieldValue;
  issues: FieldIssue[];
  auto_filled: Record<string, FieldValue>;
  next_field: string | null;
  progress: ProgressSummary | null;
  field_status: FieldStatus | null;
}

export interface ApplicationEvent {
  id: number;
  event_type: string;
  field_id: string | null;
  source: string | null;
  old_value: unknown;
  new_value: unknown;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface EventList {
  events: ApplicationEvent[];
}

// ---- Voice and agent (backend/app/schemas/agent.py, api/routes/voice.py) ----

export interface FieldHelp {
  field_id: string;
  language: string;
  label: string;
  explanation: string;
  example: string;
  where_to_find: string;
  common_mistakes: unknown;
}

export interface AgentField {
  field_id: string;
  label: string;
  value: FieldValue;
}

export interface AgentRejection {
  field_id: string;
  label: string;
  issues: FieldIssue[];
}

export interface AgentTurnResponse {
  reply: string;
  speech: string;
  intent: string;
  understood_by: "llm" | "rules" | "none";
  saved: AgentField[];
  pending_confirmation: AgentField[];
  rejected: AgentRejection[];
  help: FieldHelp | null;
  next_field: string | null;
  application: ApplicationRead;
}

export interface TranscribeResponse {
  ok: boolean;
  text: string;
  normalized: string;
  language: string;
  detected_language: string | null;
  latency_seconds: number | null;
  truncated: boolean;
  message: string | null;
  fallback: "retry" | "type" | null;
}

export interface ConversationMessage {
  id: number;
  role: string;
  channel: string;
  content: string;
  field_id: string | null;
  created_at: string;
}

// ---- Form definition (backend/app/schemas/form.py) ----

export interface FormOption {
  value: string;
  label: { en: string; kn: string };
}

export interface FormFieldDef {
  id: string;
  type: string;
  label: { en: string; kn: string };
  required: boolean;
  core: boolean;
  options: FormOption[];
  show_if: { field: string; equals: string } | null;
  calculated: boolean;
  compare_with_document: boolean;
  validation: Record<string, unknown>;
}

export interface FormSection {
  id: string;
  title: { en: string; kn: string };
  fields: FormFieldDef[];
}

export interface FormDefinition {
  form_id: string;
  version: string;
  sections: FormSection[];
}

// ---- Review and submission (backend/app/schemas/submission.py) ----

export interface ReviewItem {
  field_id: string;
  label: string;
  display: string;
  value: FieldValue;
  source: string | null;
  confirmed: boolean;
}

export interface ReviewSection {
  id: string;
  title: string;
  items: ReviewItem[];
}

export interface ReadinessIssue {
  kind: "missing" | "invalid" | "cross_field";
  field_id: string | null;
  label: string | null;
  section_id: string | null;
  section_title: string | null;
  message: string;
}

export interface ReviewRead {
  status: ApplicationStatus;
  language: Language;
  ready: boolean;
  can_submit: boolean;
  submitted: boolean;
  reference_id: string | null;
  submitted_at: string | null;
  issues: ReadinessIssue[];
  sections: ReviewSection[];
}

export interface SubmitResult {
  reference_id: string;
  submitted_at: string;
  status: ApplicationStatus;
  already_submitted: boolean;
}