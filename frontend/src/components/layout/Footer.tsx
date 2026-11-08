import Link from "next/link";

import { BANK, FOOTER_COLUMNS, PROTOTYPE_NOTICE } from "@/lib/bank";

export default function Footer() {
  return (
    <footer className="mt-auto bg-navy text-white">
      <div className="site-container grid gap-8 py-10 sm:grid-cols-2 lg:grid-cols-4">
        {FOOTER_COLUMNS.map((column) => (
          <div key={column.heading}>
            <h3 className="mb-3 text-base font-semibold text-white">
              {column.heading}
            </h3>
            <ul className="space-y-2 text-sm">
              {column.links.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-white/80 hover:text-white hover:underline"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}

        <div>
          <h3 className="mb-3 text-base font-semibold text-white">
            Contact
          </h3>
          <address className="space-y-2 text-sm not-italic text-white/80">
            <p>Helpline: {BANK.helpline}</p>
            <p>{BANK.email}</p>
            <p>{BANK.address}</p>
          </address>
        </div>
      </div>

      <div className="border-t border-white/15">
        <div className="site-container space-y-2 py-5 text-xs text-white/75">
          <p>{PROTOTYPE_NOTICE}</p>
          <p>
            &copy; {BANK.year} {BANK.name}. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}