"use client";

import { useEffect, useState } from "react";

import type { FieldIssue, FieldValue, FormFieldDef, Language } from "@/lib/types";

const SOURCE_LABEL: Record<string, Record<Language, string>> = {
  voice: { en: "Voice", kn: "ಧ್ವನಿ" },
  text: { en: "Typed", kn: "ಟೈಪ್" },
  document: { en: "From document", kn: "ದಾಖಲೆಯಿಂದ" },
  calculated: { en: "Calculated", kn: "ಲೆಕ್ಕಾಚಾರ" },
};

const TEXT = {
  confirm: { en: "Confirm", kn: "ಖಚಿತಪಡಿಸಿ" },
  confirmed: { en: "Confirmed", kn: "ಖಚಿತವಾಗಿದೆ" },
  choose: { en: "Choose...", kn: "ಆರಿಸಿ..." },
  auto: { en: "Worked out automatically", kn: "ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಲೆಕ್ಕಹಾಕಲಾಗಿದೆ" },
  autoEmpty: { en: "Fills in once the related answers are given", kn: "ಸಂಬಂಧಿತ ಉತ್ತರಗಳನ್ನು ನೀಡಿದ ನಂತರ ತುಂಬುತ್ತದೆ" },
};

const NUMERIC_TYPES = new Set(["number", "currency", "year", "percentage"]);
const PLACEHOLDERS: Record<string, string> = {
  date: "14-05-2003",
  phone: "9876543210",
  pan: "ABCPE1234F",
  aadhaar: "2345 6789 0123",
  pincode: "560001",
  email: "name@example.com",
};

interface Props {
  field: FormFieldDef;
  language: Language;
  value: FieldValue | undefined;
  source?: string;
  confirmed: boolean;
  issue?: FieldIssue;
  active: boolean;
  onSave: (fieldId: string, value: FieldValue) => void;
  onConfirm: (fieldId: string) => void;
}

export default function FormField({
  field, language, value, source, confirmed, issue, active, onSave, onConfirm,
}: Props) {
  const stored = value === undefined || value === null ? "" : String(value);
  const [draft, setDraft] = useState(stored);

  // A change from outside (the voice agent) replaces what is shown
  useEffect(() => setDraft(stored), [stored]);

  const label = field.label[language];
  const inputId = `input-${field.id}`;
  const describedBy = issue ? `${inputId}-issue` : undefined;
  const border = issue ? "border-danger" : active ? "border-accent" : "border-line";
  const inputClass = `w-full rounded border ${border} bg-white px-3 py-2 text-strong focus:border-accent`;

  const commit = () => {
    if (draft.trim() !== stored) onSave(field.id, draft.trim());
  };

  let control: React.ReactNode;
  if (field.calculated) {
    control = (
      <div className="flex flex-wrap items-center gap-3">
        <output id={inputId} className={`${inputClass} flex-1 bg-tint-light`}>
          {stored || <span className="text-muted">{TEXT.autoEmpty[language]}</span>}
        </output>
        {stored && (
          <button
            type="button"
            className={`btn ${confirmed ? "btn-secondary" : "btn-primary"} !py-1.5`}
            disabled={confirmed}
            onClick={() => onConfirm(field.id)}
          >
            {confirmed ? TEXT.confirmed[language] : TEXT.confirm[language]}
          </button>
        )}
      </div>
    );
  } else if (field.type === "choice") {
    control = (
      <select
        id={inputId}
        className={inputClass}
        value={stored}
        aria-invalid={!!issue}
        aria-describedby={describedBy}
        onChange={(event) => onSave(field.id, event.target.value)}
      >
        <option value="">{TEXT.choose[language]}</option>
        {field.options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label[language]}
          </option>
        ))}
      </select>
    );
  } else if (field.type === "checkbox") {
    control = (
      <label className="flex items-start gap-3">
        <input
          id={inputId}
          type="checkbox"
          className="mt-1 h-5 w-5 accent-[var(--eduvest-cyan)]"
          checked={value === true}
          aria-describedby={describedBy}
          onChange={(event) => onSave(field.id, event.target.checked)}
        />
        <span className="text-strong">{label}</span>
      </label>
    );
  } else if (field.type === "textarea") {
    control = (
      <textarea
        id={inputId}
        rows={3}
        className={inputClass}
        value={draft}
        aria-invalid={!!issue}
        aria-describedby={describedBy}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
      />
    );
  } else {
    control = (
      <input
        id={inputId}
        type={field.type === "email" ? "email" : field.type === "phone" ? "tel" : "text"}
        inputMode={NUMERIC_TYPES.has(field.type) ? "decimal" : ["pincode", "aadhaar"].includes(field.type) ? "numeric" : undefined}
        className={inputClass}
        value={draft}
        placeholder={PLACEHOLDERS[field.type]}
        aria-invalid={!!issue}
        aria-describedby={describedBy}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => event.key === "Enter" && commit()}
      />
    );
  }

  return (
    <div
      id={`field-${field.id}`}
      className={`rounded-md p-3 transition-colors ${active ? "bg-tint ring-2 ring-accent" : ""}`}
    >
      {field.type !== "checkbox" && (
        <label htmlFor={inputId} className="mb-1 flex flex-wrap items-center gap-2 font-semibold text-strong">
          <span>
            {label}
            {field.required && <span className="text-danger" aria-hidden="true"> *</span>}
          </span>
          {source && stored && (
            <span className="rounded bg-tint px-2 py-0.5 text-xs font-normal text-brand">
              {(SOURCE_LABEL[source] ?? SOURCE_LABEL.text)[language]}
            </span>
          )}
        </label>
      )}
      {control}
      {field.calculated && stored && (
        <p className="mt-1 text-xs text-muted">{TEXT.auto[language]}</p>
      )}
      {issue && (
        <p id={`${inputId}-issue`} role="alert" className="mt-1 text-sm text-danger">
          {issue.message} {issue.hint}
        </p>
      )}
    </div>
  );
}