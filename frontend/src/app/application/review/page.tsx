"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { Language, ReviewRead, SubmitResult } from "@/lib/types";

const TEXT = {
  title: { en: "Review your application", kn: "ನಿಮ್ಮ ಅರ್ಜಿಯನ್ನು ಪರಿಶೀಲಿಸಿ" },
  loading: { en: "Loading...", kn: "ಲೋಡ್ ಆಗುತ್ತಿದೆ..." },
  noSession: {
    en: "No application found. Please start one first.",
    kn: "ಯಾವುದೇ ಅರ್ಜಿ ಕಂಡುಬಂದಿಲ್ಲ. ದಯವಿಟ್ಟು ಮೊದಲು ಒಂದನ್ನು ಆರಂಭಿಸಿ.",
  },
  back: { en: "Back to application", kn: "ಅರ್ಜಿಗೆ ಹಿಂತಿರುಗಿ" },
  ready: {
    en: "All required details are complete and valid.",
    kn: "ಎಲ್ಲಾ ಅಗತ್ಯ ವಿವರಗಳು ಪೂರ್ಣ ಮತ್ತು ಸರಿಯಾಗಿವೆ.",
  },
  notReady: {
    en: "Please fix these items before you can submit:",
    kn: "ಸಲ್ಲಿಸುವ ಮೊದಲು ಈ ಅಂಶಗಳನ್ನು ಸರಿಪಡಿಸಿ:",
  },
  fix: { en: "Fix", kn: "ಸರಿಪಡಿಸಿ" },
  edit: { en: "Edit", kn: "ಬದಲಿಸಿ" },
  confirm: {
    en: "I confirm that the information above is correct. I understand this is a demonstration and nothing is sent to a real bank.",
    kn: "ಮೇಲಿನ ಮಾಹಿತಿ ಸರಿಯಾಗಿದೆ ಎಂದು ನಾನು ಖಚಿತಪಡಿಸುತ್ತೇನೆ. ಇದು ಪ್ರಾತ್ಯಕ್ಷಿಕೆ ಮಾತ್ರ ಮತ್ತು ನಿಜವಾದ ಬ್ಯಾಂಕ್‌ಗೆ ಏನೂ ಕಳುಹಿಸಲಾಗುವುದಿಲ್ಲ ಎಂದು ನಾನು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನೆ.",
  },
  submit: { en: "Submit application (mock)", kn: "ಅರ್ಜಿ ಸಲ್ಲಿಸಿ (ಮಾದರಿ)" },
  submitting: { en: "Submitting...", kn: "ಸಲ್ಲಿಸಲಾಗುತ್ತಿದೆ..." },
  doneTitle: { en: "Application submitted", kn: "ಅರ್ಜಿ ಸಲ್ಲಿಸಲಾಗಿದೆ" },
  reference: { en: "Your reference ID", kn: "ನಿಮ್ಮ ರೆಫರೆನ್ಸ್ ಐಡಿ" },
  mockNote: {
    en: "This is a prototype. No real application was sent, and this is not a loan approval or an eligibility decision.",
    kn: "ಇದು ಮಾದರಿ ಮಾತ್ರ. ಯಾವುದೇ ನಿಜವಾದ ಅರ್ಜಿ ಕಳುಹಿಸಲಾಗಿಲ್ಲ, ಮತ್ತು ಇದು ಸಾಲ ಮಂಜೂರಾತಿ ಅಥವಾ ಅರ್ಹತಾ ನಿರ್ಧಾರವಲ್ಲ.",
  },
  print: { en: "Print", kn: "ಪ್ರಿಂಟ್ ಮಾಡಿ" },
  home: { en: "Back to home", kn: "ಮುಖಪುಟಕ್ಕೆ" },
  source: {
    voice: { en: "Voice", kn: "ಧ್ವನಿ" },
    text: { en: "Typed", kn: "ಟೈಪ್" },
    document: { en: "Document", kn: "ದಾಖಲೆ" },
    calculated: { en: "Calculated", kn: "ಲೆಕ್ಕಾಚಾರ" },
  } as Record<string, { en: string; kn: string }>,
};

export default function ReviewPage() {
  const [review, setReview] = useState<ReviewRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasSession, setHasSession] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SubmitResult | null>(null);

  useEffect(() => {
    if (!getToken()) {
      setHasSession(false);
      setLoading(false);
      return;
    }
    api
      .getReview()
      .then(setReview)
      .catch((err) => setError(err instanceof Error ? err.message : "Something went wrong."))
      .finally(() => setLoading(false));
  }, []);

  const language: Language = review?.language ?? "en";

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      setResult(await api.submitApplication(true));
      setReview(await api.getReview());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      if (err instanceof ApiError && err.status === 409) setReview(await api.getReview());
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p className="site-container py-10 text-muted">{TEXT.loading[language]}</p>;

  if (!hasSession || !review) {
    return (
      <section className="section">
        <div className="site-container max-w-3xl card p-6 text-center">
          <p>{error ?? TEXT.noSession[language]}</p>
          <Link href="/application" className="btn btn-primary mt-4">{TEXT.back[language]}</Link>
        </div>
      </section>
    );
  }

  const referenceId = result?.reference_id ?? review.reference_id;
  const submittedAt = result?.submitted_at ?? review.submitted_at;

  return (
    <section className="section !pt-6">
      <div className="site-container max-w-3xl">
        <nav aria-label="Breadcrumb" className="mb-4 text-sm text-muted print:hidden">
          <Link href="/">Home</Link> / <Link href="/application">Apply</Link> / <span>Review</span>
        </nav>

        {review.submitted && referenceId ? (
          <div className="card mb-6 border-success p-6 text-center md:p-8" role="status">
            <h1 className="text-success">{TEXT.doneTitle[language]}</h1>
            <p className="mt-4 text-sm text-muted">{TEXT.reference[language]}</p>
            <p className="mt-1 select-all text-3xl font-bold tracking-wider text-brand">{referenceId}</p>
            {submittedAt && (
              <p className="mt-1 text-sm text-muted">{new Date(submittedAt).toLocaleString()}</p>
            )}
            <p className="mx-auto mt-4 max-w-xl text-sm">{TEXT.mockNote[language]}</p>
            <div className="mt-5 flex justify-center gap-3 print:hidden">
              <button type="button" className="btn btn-secondary" onClick={() => window.print()}>
                {TEXT.print[language]}
              </button>
              <Link href="/" className="btn btn-primary">{TEXT.home[language]}</Link>
            </div>
          </div>
        ) : (
          <h1 className="mb-4">{TEXT.title[language]}</h1>
        )}

        {!review.submitted && (
          <div
            className={`card mb-6 p-4 ${review.ready ? "border-success" : "border-warning"}`}
            role="status"
          >
            {review.ready ? (
              <p className="font-semibold text-success">✓ {TEXT.ready[language]}</p>
            ) : (
              <>
                <p className="font-semibold text-strong">{TEXT.notReady[language]}</p>
                <ul className="mt-2 space-y-2">
                  {review.issues.map((issue, index) => (
                    <li key={`${issue.field_id}-${index}`} className="flex flex-wrap items-start justify-between gap-2 text-sm">
                      <span>
                        <strong>{issue.label}</strong>
                        {issue.section_title && <span className="text-muted"> ({issue.section_title})</span>}
                        : {issue.message}
                      </span>
                      <Link href="/application" className="btn btn-secondary !py-1 !text-xs print:hidden">
                        {TEXT.fix[language]}
                      </Link>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        <div className="space-y-4">
          {review.sections.map((section) => (
            <div key={section.id} className="card p-4 md:p-5">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="!text-lg">{section.title}</h2>
                {!review.submitted && (
                  <Link href="/application" className="text-sm print:hidden">{TEXT.edit[language]}</Link>
                )}
              </div>
              <dl className="divide-y divide-line">
                {section.items.map((item) => (
                  <div key={item.field_id} className="grid gap-1 py-2 sm:grid-cols-[1fr_1.2fr]">
                    <dt className="text-sm text-muted">{item.label}</dt>
                    <dd className="font-semibold text-strong">
                      {item.display}
                      {item.source && TEXT.source[item.source] && (
                        <span className="ml-2 rounded bg-tint px-2 py-0.5 text-xs font-normal text-brand print:hidden">
                          {TEXT.source[item.source][language]}
                        </span>
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>

        {!review.submitted && (
          <div className="card mt-6 p-4 md:p-5 print:hidden">
            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-1 h-5 w-5"
                checked={confirmed}
                disabled={!review.can_submit}
                onChange={(event) => setConfirmed(event.target.checked)}
              />
              <span>{TEXT.confirm[language]}</span>
            </label>
            {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
            <button
              type="button"
              className="btn btn-primary mt-4 w-full"
              disabled={!review.can_submit || !confirmed || submitting}
              onClick={() => void submit()}
            >
              {submitting ? TEXT.submitting[language] : TEXT.submit[language]}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}