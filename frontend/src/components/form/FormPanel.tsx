"use client";

import { useEffect, useMemo, useState } from "react";

import FormField from "@/components/form/FormField";
import type {
  ApplicationRead, FieldValue, FormDefinition, FormFieldDef, Language,
} from "@/lib/types";

const TEXT = {
  back: { en: "Previous section", kn: "ಹಿಂದಿನ ವಿಭಾಗ" },
  next: { en: "Next section", kn: "ಮುಂದಿನ ವಿಭಾಗ" },
};

function isVisible(field: FormFieldDef, values: ApplicationRead["values"]): boolean {
  return !field.show_if || values[field.show_if.field] === field.show_if.equals;
}

interface Props {
  form: FormDefinition;
  application: ApplicationRead;
  language: Language;
  onSave: (fieldId: string, value: FieldValue) => void;
  onConfirm: (fieldId: string) => void;
}

export default function FormPanel({ form, application, language, onSave, onConfirm }: Props) {
  const [activeId, setActiveId] = useState(form.sections[0]?.id ?? "");
  const currentField = application.current_field;

  // Follow the assistant: show the section of the field it is asking about
  useEffect(() => {
    if (!currentField) return;
    const section = form.sections.find((s) => s.fields.some((f) => f.id === currentField));
    if (section) setActiveId(section.id);
    const timer = setTimeout(() => {
      document.getElementById(`field-${currentField}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 80);
    return () => clearTimeout(timer);
  }, [currentField, form.sections]);

  const index = Math.max(0, form.sections.findIndex((s) => s.id === activeId));
  const section = form.sections[index];

  const progressBySection = useMemo(
    () => new Map((application.progress?.sections ?? []).map((s) => [s.section_id, s])),
    [application.progress]
  );
  const issues = useMemo(
    () => new Map((application.field_status?.invalid ?? []).map((i) => [i.field_id, i])),
    [application.field_status]
  );

  if (!section) return null;

  return (
    <div className="min-w-0">
      <nav aria-label="Sections" className="mb-4 flex gap-2 overflow-x-auto pb-1">
        {form.sections.map((s) => {
          const progress = progressBySection.get(s.id);
          const done = !!progress && progress.total > 0 && progress.answered >= progress.total;
          const selected = s.id === section.id;
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => setActiveId(s.id)}
              aria-current={selected ? "step" : undefined}
              className={`whitespace-nowrap rounded-full border px-3 py-1.5 text-sm font-semibold ${
                selected ? "border-brand bg-brand text-white" : "border-line bg-white text-brand"
              }`}
            >
              {done && <span aria-hidden="true">✓ </span>}
              {s.title[language]}
              {progress && progress.total > 0 && (
                <span className={`ml-2 text-xs ${selected ? "text-white/80" : "text-muted"}`}>
                  {progress.answered}/{progress.total}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="card p-4 md:p-6">
        <h2 className="mb-4">{section.title[language]}</h2>
        <div className="space-y-2">
          {section.fields
            .filter((field) => isVisible(field, application.values))
            .map((field) => (
              <FormField
                key={field.id}
                field={field}
                language={language}
                value={application.values[field.id]}
                source={application.field_sources[field.id]}
                confirmed={application.confirmed_fields.includes(field.id)}
                issue={issues.get(field.id)}
                active={field.id === currentField}
                onSave={onSave}
                onConfirm={onConfirm}
              />
            ))}
        </div>

        <div className="mt-6 flex justify-between">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={index === 0}
            onClick={() => setActiveId(form.sections[index - 1].id)}
          >
            {TEXT.back[language]}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={index === form.sections.length - 1}
            onClick={() => setActiveId(form.sections[index + 1].id)}
          >
            {TEXT.next[language]}
          </button>
        </div>
      </div>
    </div>
  );
}