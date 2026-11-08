import Link from "next/link";

import { BANK } from "@/lib/bank";

function MicIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
      <path
        d="M5 11 C5 15 8 18 12 18 C16 18 19 15 19 11 M12 18 V21 M8 21 H16"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function Hero() {
  return (
    <section className="bg-gradient-to-r from-navy via-brand to-brand-dark text-white">
      <div className="site-container grid items-center gap-8 py-12 md:grid-cols-2 md:py-16">
        <div>
          <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-accent">
            {BANK.name} Education Loan
          </p>
          <h1 className="!text-white">
            Study your dream course. We will help you fund it.
          </h1>
          <p className="mt-4 max-w-xl text-white/90">
            Apply for your education loan with the help of Dhwani, our voice
            assistant. Speak in Kannada or English and Dhwani will guide you
            through every field of the application.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/application" className="btn btn-primary">
              Apply Now
            </Link>
            <Link
              href="/education-loan"
              className="btn btn-secondary !border-white !text-white hover:!bg-white hover:!text-brand"
            >
              Know More
            </Link>
          </div>
        </div>

        {/* Voice assistant callout */}
        <div className="card mx-auto w-full max-w-md p-6 text-strong">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-accent text-white">
              <MicIcon />
            </span>
            <div>
              <h2 className="!text-xl">Meet Dhwani</h2>
              <p className="text-sm text-muted">Your voice application guide</p>
            </div>
          </div>
          <p className="mt-4 text-lg font-semibold text-brand">
            ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಿ
          </p>
          <p className="text-sm text-body">Or speak in English. Typing works too.</p>
          <ul className="mt-4 space-y-2 text-sm text-body">
            <li>&#10003; Understand what each field means</li>
            <li>&#10003; Get instant feedback on your answers</li>
            <li>&#10003; Upload your marks card and check it automatically</li>
          </ul>
        </div>
      </div>
    </section>
  );
}