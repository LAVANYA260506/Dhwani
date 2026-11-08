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