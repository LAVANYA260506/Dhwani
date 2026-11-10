"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import FormPanel from "@/components/form/FormPanel";
import VoicePanel from "@/components/voice/VoicePanel";
import { useApplication } from "@/hooks/useApplication";
import { useVoiceAgent } from "@/hooks/useVoiceAgent";
import { getForm } from "@/lib/formApi";
import { PROTOTYPE_NOTICE } from "@/lib/bank";
import type { FormDefinition, Language } from "@/lib/types";

const TEXT = {
  startTitle: { en: "Apply for an education loan", kn: "ಶಿಕ್ಷಣ ಸಾಲಕ್ಕೆ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ" },
  startIntro: {
    en: "Choose your language. You can speak or type your answers.",
    kn: "ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ಆರಿಸಿ. ನೀವು ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ ಉತ್ತರಿಸಬಹುದು.",
  },
  consent: {
    en: "I agree to share my details for this demonstration. This is a prototype: nothing is submitted to a real bank.",
    kn: "ಈ ಪ್ರಾತ್ಯಕ್ಷಿಕೆಗಾಗಿ ನನ್ನ ವಿವರಗಳನ್ನು ಹಂಚಿಕೊಳ್ಳಲು ನಾನು ಒಪ್ಪುತ್ತೇನೆ. ಇದು ಮಾದರಿ ಮಾತ್ರ: ಯಾವುದೇ ನಿಜವಾದ ಬ್ಯಾಂಕ್‌ಗೆ ಏನೂ ಸಲ್ಲಿಕೆಯಾಗುವುದಿಲ್ಲ.",
  },
  start: { en: "Start application", kn: "ಅರ್ಜಿ ಆರಂಭಿಸಿ" },
  title: { en: "Education loan application", kn: "ಶಿಕ್ಷಣ ಸಾಲದ ಅರ್ಜಿ" },
  complete: { en: "Review application", kn: "ಅರ್ಜಿಯನ್ನು ಪರಿಶೀಲಿಸಿ" },
  startOver: { en: "Start over", kn: "ಮತ್ತೆ ಆರಂಭಿಸಿ" },
  loading: { en: "Loading...", kn: "ಲೋಡ್ ಆಗುತ್ತಿದೆ..." },
  formError: {
    en: "Could not load the form. Is the server running?",
    kn: "ಅರ್ಜಿಯನ್ನು ಲೋಡ್ ಮಾಡಲಾಗಲಿಲ್ಲ. ಸರ್ವರ್ ಚಾಲನೆಯಲ್ಲಿದೆಯೇ?",
  },
  submitted: {
    en: "This application has been submitted. Reference ID:",
    kn: "ಈ ಅರ್ಜಿಯನ್ನು ಸಲ್ಲಿಸಲಾಗಿದೆ. ರೆಫರೆನ್ಸ್ ಐಡಿ:",
  },
  view: { en: "View", kn: "ವೀಕ್ಷಿಸಿ" },
};

function StartScreen({
  onStart,
  error,
}: {
  onStart: (language: Language, consent: boolean) => void;
  error: string | null;
}) {
  const [language, setLanguage] = useState<Language>("kn");
  const [consent, setConsent] = useState(false);

  return (
    <section className="section">
      <div className="site-container max-w-xl">
        <div className="card p-6 md:p-8">
          <h1>{TEXT.startTitle[language]}</h1>
          <p className="mt-3">{TEXT.startIntro[language]}</p>

          <div className="mt-5 flex gap-3" role="group" aria-label="Language">
            {(["kn", "en"] as const).map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => setLanguage(code)}
                aria-pressed={language === code}
                className={`btn flex-1 ${language === code ? "btn-primary" : "btn-secondary"}`}
              >
                {code === "kn" ? "ಕನ್ನಡ" : "English"}
              </button>
            ))}
          </div>

          <label className="mt-5 flex items-start gap-3 text-sm">
            <input
              type="checkbox"
              className="mt-1 h-5 w-5"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            <span>{TEXT.consent[language]}</span>
          </label>

          {error && (
            <p role="alert" className="mt-3 text-sm text-danger">
              {error}
            </p>
          )}

          <button
            type="button"
            className="btn btn-primary mt-6 w-full"
            disabled={!consent}
            onClick={() => onStart(language, consent)}
          >
            {TEXT.start[language]}
          </button>
        </div>
        <p className="mt-4 text-center text-xs text-muted">{PROTOTYPE_NOTICE}</p>
      </div>
    </section>
  );
}

export default function ApplicationPage() {
  const {
    application,
    loading,
    error,
    start,
    saveField,
    confirmField,
    changeLanguage,
    refresh,
    reset,
  } = useApplication();
  const language: Language = application?.language ?? "en";

  const [form, setForm] = useState<FormDefinition | null>(null);
  const [formFailed, setFormFailed] = useState(false);
  useEffect(() => {
    getForm()
      .then(setForm)
      .catch(() => setFormFailed(true));
  }, []);

  const voice = useVoiceAgent({
    enabled: !!application,
    language,
    currentField: application?.current_field ?? null,
    onTurn: () => {
      void refresh(); // the agent saved answers on the server: reload them
    },
  });

  if (loading) {
    return <p className="site-container py-10 text-muted">{TEXT.loading[language]}</p>;
  }
  if (!application) {
    return <StartScreen onStart={start} error={error} />;
  }

  const progress = application.progress;

  return (
    <section className="section !pt-6">
      <div className="site-container">
        <nav aria-label="Breadcrumb" className="mb-3 text-sm text-muted">
          <Link href="/">Home</Link> / <span>Apply</span>
        </nav>

        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h1 className="!text-2xl">{TEXT.title[language]}</h1>
          <div className="flex items-center gap-2">
            {(["kn", "en"] as const).map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => void changeLanguage(code)}
                aria-pressed={language === code}
                className={`btn !py-1.5 ${language === code ? "btn-primary" : "btn-secondary"}`}
              >
                {code === "kn" ? "ಕನ್ನಡ" : "English"}
              </button>
            ))}
            <button type="button" className="text-sm text-muted underline" onClick={reset}>
              {TEXT.startOver[language]}
            </button>
          </div>
        </div>

        {progress && (
          <div className="mb-5">
            <div className="mb-1 flex justify-between text-sm text-muted">
              <span>
                {progress.answered_required}/{progress.total_required}
              </span>
              <span>{progress.percent}%</span>
            </div>
            <div
              className="h-2 overflow-hidden rounded bg-line"
              role="progressbar"
              aria-valuenow={progress.percent}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full bg-accent transition-all"
                style={{ width: `${progress.percent}%` }}
              />
            </div>
          </div>
        )}

        {error && (
          <p role="alert" className="mb-3 text-sm text-danger">
            {error}
          </p>
        )}

        {application.status === "submitted" && (
          <p className="mb-4 rounded border border-success bg-white p-3 text-sm text-strong">
            ✓ {TEXT.submitted[language]} <strong>{application.reference_id}</strong>{" "}
            <Link href="/application/review">{TEXT.view[language]}</Link>
          </p>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="order-2 min-w-0 lg:order-1">
            {form ? (
              <FormPanel
                form={form}
                application={application}
                language={language}
                onSave={(fieldId, value) => void saveField(fieldId, value, "text")}
                onConfirm={(fieldId) => void confirmField(fieldId)}
              />
            ) : (
              <p className="text-muted">
                {formFailed ? TEXT.formError[language] : TEXT.loading[language]}
              </p>
            )}

            {progress?.complete && (
              <div className="mt-6 text-center">
                <Link href="/application/review" className="btn btn-primary">
                  {TEXT.complete[language]}
                </Link>
              </div>
            )}
          </div>

          <div className="order-1 min-w-0 lg:order-2">
            <div className="lg:sticky lg:top-4">
              <VoicePanel voice={voice} language={language} />
            </div>
          </div>
        </div>

        <p className="mt-8 text-center text-xs text-muted">{PROTOTYPE_NOTICE}</p>
      </div>
    </section>
  );
}