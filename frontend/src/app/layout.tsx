import type { Metadata } from "next";
import { Open_Sans, Noto_Sans_Kannada } from "next/font/google";
import "./globals.css";

import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import { BANK } from "@/lib/bank";

const openSans = Open_Sans({
  subsets: ["latin"],
  variable: "--font-open-sans",
  display: "swap",
});

const notoKannada = Noto_Sans_Kannada({
  subsets: ["kannada"],
  variable: "--font-noto-kannada",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: `${BANK.name} - ${BANK.tagline}`,
    template: `%s | ${BANK.name}`,
  },
  description:
    "EduVest education loan application with Dhwani, a Kannada and English voice assistant. Prototype demonstration only.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${openSans.variable} ${notoKannada.variable}`}>
      <body className="flex min-h-screen flex-col">
        <Header />
        <main id="main-content" className="flex-1">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}