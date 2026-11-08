import Link from "next/link";

import { QUICK_ACTIONS } from "@/lib/bank";

export default function QuickActions() {
  return (
    <section aria-labelledby="quick-actions-heading" className="bg-white">
      <div className="site-container -mt-0 py-8">
        <h2 id="quick-actions-heading" className="sr-only">
          Quick actions
        </h2>
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {QUICK_ACTIONS.map((action) => (
            <li key={action.title}>
              <Link
                href={action.href}
                className="card group flex h-full flex-col border-t-4 border-t-accent p-5 transition hover:-translate-y-0.5 hover:no-underline hover:shadow-lg"
              >
                <span className="text-lg font-semibold text-brand group-hover:text-brand-dark">
                  {action.title}
                </span>
                <span className="mt-1 text-sm text-muted">
                  {action.description}
                </span>
                <span className="mt-auto pt-4 text-sm font-semibold text-accent-dark">
                  Go &rarr;
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}