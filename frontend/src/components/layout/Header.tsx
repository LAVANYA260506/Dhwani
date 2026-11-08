"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { BANK, MAIN_NAV, UTILITY_LINKS } from "@/lib/bank";

function LogoMark() {
  // Simple original mark (not any real bank's logo)
  return (
    <svg
      width="44"
      height="44"
      viewBox="0 0 44 44"
      aria-hidden="true"
      className="shrink-0"
    >
      <circle cx="22" cy="22" r="22" fill="var(--eduvest-blue)" />
      <path
        d="M22 9 L36 16 L22 23 L8 16 Z"
        fill="#fff"
      />
      <path
        d="M14 20.5 V26 C14 28.5 17.6 31 22 31 C26.4 31 30 28.5 30 26 V20.5 L22 24.5 Z"
        fill="var(--eduvest-cyan)"
      />
    </svg>
  );
}

export default function Header() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const isActive = (href: string) =>
    href !== "#" && (href === "/" ? pathname === "/" : pathname.startsWith(href));

  return (
    <header className="w-full">
      {/* Utility bar */}
      <div className="bg-navy text-white">
        <div className="site-container flex items-center justify-between py-1.5 text-xs">
          <ul className="flex items-center gap-4">
            {UTILITY_LINKS.map((link) => (
              <li key={link.label}>
                <a
                  href={link.href}
                  className="text-white/90 hover:text-white hover:underline"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
          <span className="hidden text-white/90 sm:inline">
            Helpline: {BANK.helpline}
          </span>
        </div>
      </div>

      {/* Logo bar */}
      <div className="border-b border-line bg-white">
        <div className="site-container flex items-center justify-between py-3">
          <Link
            href="/"
            className="flex items-center gap-3 hover:no-underline"
            aria-label={`${BANK.name} home`}
          >
            <LogoMark />
            <span className="leading-tight">
              <span className="block text-2xl font-bold text-brand">
                {BANK.name}
              </span>
              <span className="block text-xs text-muted">{BANK.tagline}</span>
            </span>
          </Link>

          <div className="hidden items-center gap-3 md:flex">
            <a href="#" className="btn btn-secondary !py-2">
              Register
            </a>
            <a href="#" className="btn btn-primary !py-2">
              Login
            </a>
          </div>

          {/* Mobile menu button */}
          <button
            type="button"
            className="rounded border border-line p-2 text-brand md:hidden"
            aria-label="Toggle navigation menu"
            aria-expanded={menuOpen}
            aria-controls="main-nav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
              {menuOpen ? (
                <path
                  d="M5 5 L19 19 M19 5 L5 19"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              ) : (
                <path
                  d="M4 7 H20 M4 12 H20 M4 17 H20"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Main navigation */}
      <nav
        id="main-nav"
        aria-label="Main navigation"
        className={`bg-brand text-white ${menuOpen ? "block" : "hidden"} md:block`}
      >
        <ul className="site-container flex flex-col md:flex-row md:items-center">
          {MAIN_NAV.map((link) => (
            <li key={link.label}>
              <Link
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className={`block px-4 py-3 text-sm font-semibold text-white hover:bg-brand-dark hover:no-underline ${
                  isActive(link.href) ? "bg-brand-dark" : ""
                }`}
              >
                {link.label}
              </Link>
            </li>
          ))}
          <li className="flex gap-3 px-4 py-3 md:hidden">
            <a href="#" className="btn btn-secondary !border-white !text-white">
              Register
            </a>
            <a href="#" className="btn btn-primary">
              Login
            </a>
          </li>
        </ul>
      </nav>
    </header>
  );
}