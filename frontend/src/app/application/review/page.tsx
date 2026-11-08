import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Review Application",
};

// Placeholder: the readiness summary and mock submission are built in Phase 15.
export default function ReviewPage() {
  return (
    <section className="section">
      <div className="site-container max-w-3xl">
        <nav aria-label="Breadcrumb" className="mb-4 text-sm text-muted">
          <Link href="/">Home</Link> /{" "}
          <Link href="/application">Apply</Link> / <span>Review</span>
        </nav>

        <div className="card p-6 text-center md:p-8">
          <h1>Review your application</h1>
          <p className="mt-3 text-body">
            Your application summary and final confirmation will appear here.
          </p>
          <Link href="/application" className="btn btn-secondary mt-6">
            Back to application
          </Link>
        </div>
      </div>
    </section>
  );
}