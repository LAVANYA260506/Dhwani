"use client";

import Link from "next/link";
import { useState } from "react";

import { BANK, PROTOTYPE_NOTICE } from "@/lib/bank";

type Language = "en" | "kn";

const T = {
  title: { en: "Education Loan", kn: "ಶಿಕ್ಷಣ ಸಾಲ" },
  intro: {
    en: `Fund your studies in India or abroad with ${BANK.name}. Apply in Kannada or English, by voice or by typing, with Dhwani guiding you through every field.`,
    kn: `${BANK.name} ಜೊತೆ ಭಾರತದಲ್ಲಿ ಅಥವಾ ವಿದೇಶದಲ್ಲಿ ನಿಮ್ಮ ಶಿಕ್ಷಣಕ್ಕೆ ಹಣಕಾಸು ಪಡೆಯಿರಿ. ಧ್ವನಿ ಸಹಾಯಕ ಪ್ರತಿ ಹಂತದಲ್ಲೂ ಮಾರ್ಗದರ್ಶನ ನೀಡುತ್ತದೆ; ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ, ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ.`,
  },
  apply: { en: "Apply now", kn: "ಈಗ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ" },
  talk: { en: "Talk to Dhwani", kn: "ಧ್ವನಿಯೊಂದಿಗೆ ಮಾತನಾಡಿ" },
  featuresTitle: { en: "Key features", kn: "ಮುಖ್ಯ ವೈಶಿಷ್ಟ್ಯಗಳು" },
  eligibilityTitle: { en: "Who can apply", kn: "ಯಾರು ಅರ್ಜಿ ಸಲ್ಲಿಸಬಹುದು" },
  documentsTitle: { en: "Documents you will need", kn: "ನಿಮಗೆ ಬೇಕಾದ ದಾಖಲೆಗಳು" },
  stepsTitle: { en: "How it works", kn: "ಇದು ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ" },
  faqTitle: { en: "Common questions", kn: "ಸಾಮಾನ್ಯ ಪ್ರಶ್ನೆಗಳು" },
  note: {
    en: "Figures shown are for this demonstration only and are not a real offer.",
    kn: "ತೋರಿಸಿದ ಅಂಕಿಅಂಶಗಳು ಈ ಪ್ರಾತ್ಯಕ್ಷಿಕೆಗೆ ಮಾತ್ರ; ಇದು ನಿಜವಾದ ಕೊಡುಗೆಯಲ್ಲ.",
  },
};

const FEATURES = [
  {
    value: "₹10,000 – ₹1.5 crore",
    label: { en: "Loan amount you can request", kn: "ನೀವು ಕೇಳಬಹುದಾದ ಸಾಲದ ಮೊತ್ತ" },
  },
  {
    value: "1 – 15 years",
    label: { en: "Repayment period", kn: "ಮರುಪಾವತಿ ಅವಧಿ" },
  },
  {
    value: "India & abroad",
    label: { en: "Where you study", kn: "ನೀವು ಓದುವ ಸ್ಥಳ" },
  },
  {
    value: "Kannada & English",
    label: { en: "Apply by voice or typing", kn: "ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ" },
  },
];

const ELIGIBILITY = [
  {
    en: "Indian student with a confirmed or awaited admission to a recognised course",
    kn: "ಮಾನ್ಯತೆ ಪಡೆದ ಕೋರ್ಸ್‌ಗೆ ಖಚಿತ ಅಥವಾ ನಿರೀಕ್ಷಿತ ಪ್ರವೇಶ ಹೊಂದಿರುವ ಭಾರತೀಯ ವಿದ್ಯಾರ್ಥಿ",
  },
  {
    en: "Age between 16 and 45 years",
    kn: "16 ರಿಂದ 45 ವರ್ಷ ವಯಸ್ಸು",
  },
  {
    en: "A parent, guardian or other co-applicant with a regular income",
    kn: "ನಿಯಮಿತ ಆದಾಯವಿರುವ ಪೋಷಕರು, ಪಾಲಕರು ಅಥವಾ ಸಹ-ಅರ್ಜಿದಾರರು",
  },
  {
    en: "Undergraduate, postgraduate, diploma or PhD courses",
    kn: "ಪದವಿ, ಸ್ನಾತಕೋತ್ತರ, ಡಿಪ್ಲೊಮಾ ಅಥವಾ ಪಿಎಚ್‌ಡಿ ಕೋರ್ಸ್‌ಗಳು",
  },
];

const DOCUMENTS = [
  { en: "Aadhaar number and PAN (if you have one)", kn: "ಆಧಾರ್ ಸಂಖ್ಯೆ ಮತ್ತು ಪ್ಯಾನ್ (ಇದ್ದರೆ)" },
  { en: "Academic marks card of your last qualifying exam", kn: "ನಿಮ್ಮ ಕೊನೆಯ ಅರ್ಹತಾ ಪರೀಕ್ಷೆಯ ಅಂಕಪಟ್ಟಿ" },
  { en: "Admission letter and fee structure of the institution", kn: "ಸಂಸ್ಥೆಯ ಪ್ರವೇಶ ಪತ್ರ ಮತ್ತು ಶುಲ್ಕ ವಿವರ" },
  { en: "Co-applicant details: PAN, income and existing EMIs", kn: "ಸಹ-ಅರ್ಜಿದಾರರ ವಿವರಗಳು: ಪ್ಯಾನ್, ಆದಾಯ ಮತ್ತು ಈಗಿರುವ ಇಎಂಐಗಳು" },
];

const STEPS = [
  { en: "Choose Kannada or English and start your application.", kn: "ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್ ಆರಿಸಿ ಮತ್ತು ಅರ್ಜಿ ಆರಂಭಿಸಿ." },
  { en: "Speak your answers or type them. Dhwani explains any field you do not understand.", kn: "ಉತ್ತರಗಳನ್ನು ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ. ಅರ್ಥವಾಗದ ಕ್ಷೇತ್ರವನ್ನು ಧ್ವನಿ ವಿವರಿಸುತ್ತದೆ." },
  { en: "Dhwani reads back important details before saving them.", kn: "ಮುಖ್ಯ ವಿವರಗಳನ್ನು ಉಳಿಸುವ ಮೊದಲು ಧ್ವನಿ ಓದಿ ಹೇಳುತ್ತದೆ." },
  { en: "Review your full application and confirm to submit.", kn: "ನಿಮ್ಮ ಸಂಪೂರ್ಣ ಅರ್ಜಿಯನ್ನು ಪರಿಶೀಲಿಸಿ ಮತ್ತು ಸಲ್ಲಿಸಲು ಖಚಿತಪಡಿಸಿ." },
];

const FAQ = [
  {
    q: { en: "Can I fill the form in Kannada?", kn: "ನಾನು ಅರ್ಜಿಯನ್ನು ಕನ್ನಡದಲ್ಲಿ ತುಂಬಬಹುದೇ?" },
    a: {
      en: "Yes. You can speak or type in Kannada, English, or a mix of both.",
      kn: "ಹೌದು. ನೀವು ಕನ್ನಡ, ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಎರಡರ ಮಿಶ್ರಣದಲ್ಲಿ ಮಾತನಾಡಬಹುದು ಅಥವಾ ಟೈಪ್ ಮಾಡಬಹುದು.",
    },
  },
  {
    q: { en: "What if Dhwani hears something wrong?", kn: "ಧ್ವನಿಗೆ ತಪ್ಪಾಗಿ ಕೇಳಿಸಿದರೆ ಏನು?" },
    a: {
      en: "Important details are read back before they are saved. Say no and repeat, or type the answer instead.",
      kn: "ಮುಖ್ಯ ವಿವರಗಳನ್ನು ಉಳಿಸುವ ಮೊದಲು ಓದಿ ಹೇಳಲಾಗುತ್ತದೆ. ಇಲ್ಲ ಎಂದು ಹೇಳಿ ಮತ್ತೆ ಹೇಳಿ, ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.",
    },
  },
  {
    q: { en: "Is this a real loan application?", kn: "ಇದು ನಿಜವಾದ ಸಾಲದ ಅರ್ಜಿಯೇ?" },
    a: {
      en: "No. EduVest is a fictional bank used for a prototype demonstration. Nothing is sent to a real bank and no loan is approved.",
      kn: "ಇಲ್ಲ. ಎಡ್ಯೂವೆಸ್ಟ್ ಒಂದು ಕಾಲ್ಪನಿಕ ಬ್ಯಾಂಕ್, ಮಾದರಿ ಪ್ರಾತ್ಯಕ್ಷಿಕೆಗಾಗಿ ಮಾತ್ರ. ಯಾವುದೇ ನಿಜವಾದ ಬ್ಯಾಂಕ್‌ಗೆ ಏನೂ ಕಳುಹಿಸಲಾಗುವುದಿಲ್ಲ ಮತ್ತು ಯಾವುದೇ ಸಾಲ ಮಂಜೂರಾಗುವುದಿಲ್ಲ.",
    },
  },
];

function Check() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" className="mt-0.5 shrink-0">
      <circle cx="10" cy="10" r="10" fill="var(--eduvest-cyan)" />
      <path d="M5.5 10.5 L8.5 13.5 L14.5 7" stroke="#fff" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function EducationLoanPage() {
  const [language, setLanguage] = useState<Language>("en");

  return (
    <>
      {/* Banner */}
      <section className="bg-tint">
        <div className="site-container py-10 md:py-14">
          <nav aria-label="Breadcrumb" className="mb-4 text-sm text-muted">
            <Link href="/">Home</Link> / <Link href="/education-loan">Loans</Link> / <span>{T.title[language]}</span>
          </nav>

          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-2xl">
              <h1>{T.title[language]}</h1>
              <p className="mt-3 text-lg">{T.intro[language]}</p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link href="/application" className="btn btn-primary">{T.apply[language]}</Link>
                <Link href="/application" className="btn btn-secondary">{T.talk[language]}</Link>
              </div>
            </div>

            <div className="flex gap-2" role="group" aria-label="Language">
              {(["kn", "en"] as const).map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLanguage(code)}
                  aria-pressed={language === code}
                  className={`btn !py-1.5 ${language === code ? "btn-primary" : "btn-secondary"}`}
                >
                  {code === "kn" ? "ಕನ್ನಡ" : "English"}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="section">
        <div className="site-container">
          <h2 className="mb-6">{T.featuresTitle[language]}</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((feature) => (
              <div key={feature.value} className="card p-5">
                <p className="text-xl font-bold text-brand">{feature.value}</p>
                <p className="mt-1 text-sm text-muted">{feature.label[language]}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted">{T.note[language]}</p>
        </div>
      </section>

      {/* Eligibility and documents */}
      <section className="section !pt-0">
        <div className="site-container grid gap-6 md:grid-cols-2">
          <div className="card p-6">
            <h2 className="mb-4 !text-xl">{T.eligibilityTitle[language]}</h2>
            <ul className="space-y-3">
              {ELIGIBILITY.map((item) => (
                <li key={item.en} className="flex gap-3"><Check /><span>{item[language]}</span></li>
              ))}
            </ul>
          </div>
          <div className="card p-6">
            <h2 className="mb-4 !text-xl">{T.documentsTitle[language]}</h2>
            <ul className="space-y-3">
              {DOCUMENTS.map((item) => (
                <li key={item.en} className="flex gap-3"><Check /><span>{item[language]}</span></li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Steps */}
      <section className="section bg-white !py-10">
        <div className="site-container">
          <h2 className="mb-6">{T.stepsTitle[language]}</h2>
          <ol className="grid gap-4 md:grid-cols-4">
            {STEPS.map((step, index) => (
              <li key={step.en} className="card p-5">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand font-bold text-white">
                  {index + 1}
                </span>
                <p className="mt-3 text-sm">{step[language]}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* FAQ */}
      <section className="section">
        <div className="site-container max-w-3xl">
          <h2 className="mb-6">{T.faqTitle[language]}</h2>
          <div className="space-y-3">
            {FAQ.map((item) => (
              <details key={item.q.en} className="card p-4">
                <summary className="cursor-pointer font-semibold text-strong">{item.q[language]}</summary>
                <p className="mt-2 text-sm">{item.a[language]}</p>
              </details>
            ))}
          </div>

          <div className="mt-8 text-center">
            <Link href="/application" className="btn btn-primary">{T.apply[language]}</Link>
          </div>
          <p className="mt-6 text-center text-xs text-muted">{PROTOTYPE_NOTICE}</p>
        </div>
      </section>
    </>
  );
}