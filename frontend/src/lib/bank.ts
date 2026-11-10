/**
 * EduVest - fictional bank identity.
 * Single source for the bank name, tagline, navigation and shared site text.
 * To rename the bank, change BANK.name here only.
 */

export const BANK = {
  name: "EduVest",
  tagline: "Invest in your education",
  shortTagline: "Simple. Secure. Student-first.",
  helpline: "1800-000-0000",
  email: "support@eduvest.example",
  address: "EduVest Tower, MG Road, Bengaluru, Karnataka 560001",
  year: new Date().getFullYear(),
} as const;

export interface NavLink {
  label: string;
  href: string;
}

/** Thin bar at the very top of the page (SBI-style utility links). */
export const UTILITY_LINKS: NavLink[] = [
  { label: "Skip to main content", href: "#main-content" },
  { label: "Locate Branch", href: "#" },
  { label: "Contact Us", href: "#" },
  { label: "Customer Care", href: "#" },
];

/** Primary navigation under the logo. */
export const MAIN_NAV: NavLink[] = [
  { label: "Personal Banking", href: "#" },
  { label: "Loans", href: "/education-loan" },
  { label: "Deposits", href: "#" },
  { label: "Cards", href: "#" },
  { label: "Insurance", href: "#" },
  { label: "Education Loan", href: "/education-loan" },
];

/** Quick-action tiles shown under the hero banner on the landing page. */
export interface QuickAction {
  title: string;
  description: string;
  href: string;
}

export const QUICK_ACTIONS: QuickAction[] = [
  {
    title: "Apply for Education Loan",
    description: "Start your application in Kannada or English",
    href: "/application",
  },
  {
    title: "Education Loan Details",
    description: "Eligibility, documents and features",
    href: "/education-loan",
  },
  {
    title: "Talk to Dhwani",
    description: "Voice assistant to guide your application",
    href: "/application",
  },
  {
    title: "Find a Branch",
    description: "Locate the nearest EduVest branch",
    href: "#",
  },
];

/** Footer link columns. */
export const FOOTER_COLUMNS: { heading: string; links: NavLink[] }[] = [
  {
    heading: "Products",
    links: [
      { label: "Education Loan", href: "/education-loan" },
      { label: "Savings Account", href: "#" },
      { label: "Fixed Deposit", href: "#" },
      { label: "Credit Cards", href: "#" },
    ],
  },
  {
    heading: "Support",
    links: [
      { label: "Contact Us", href: "#" },
      { label: "Locate Branch", href: "#" },
      { label: "FAQs", href: "#" },
      { label: "Grievance Redressal", href: "#" },
    ],
  },
  {
    heading: "About",
    links: [
      { label: "About EduVest", href: "#" },
      { label: "Careers", href: "#" },
      { label: "Privacy Policy", href: "#" },
      { label: "Terms of Use", href: "#" },
    ],
  },
];

/** Shown in the footer and on the application page. */
export const PROTOTYPE_NOTICE =
  "EduVest is a fictional bank created for a prototype demonstration. " +
  "No real loan application, submission or approval takes place. " +
  "Please use made-up details only. Applications are deleted automatically after 24 hours.";