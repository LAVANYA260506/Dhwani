import Link from "next/link";

interface Product {
  title: string;
  description: string;
  href: string;
  featured?: boolean;
}

const PRODUCTS: Product[] = [
  {
    title: "Education Loan",
    description:
      "Funding for tuition, hostel and study expenses for courses in India and abroad. Apply with voice guidance in Kannada or English.",
    href: "/education-loan",
    featured: true,
  },
  {
    title: "Student Savings Account",
    description:
      "A zero-hassle account for students to manage allowances, scholarships and daily spending.",
    href: "#",
  },
  {
    title: "Fixed Deposit",
    description:
      "Grow your savings with flexible tenures and simple online booking.",
    href: "#",
  },
  {
    title: "Student Credit Card",
    description:
      "Build a credit history early with a card designed for students and first-time users.",
    href: "#",
  },
];

export default function ProductCards() {
  return (
    <section
      aria-labelledby="products-heading"
      className="section bg-tint-light"
    >
      <div className="site-container">
        <div className="mb-8 text-center">
          <h2 id="products-heading">Our Products</h2>
          <p className="mx-auto mt-2 max-w-2xl text-muted">
            Banking built around students and their families.
          </p>
        </div>

        <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {PRODUCTS.map((product) => (
            <li key={product.title}>
              <div
                className={`card flex h-full flex-col p-6 ${
                  product.featured ? "border-2 !border-accent" : ""
                }`}
              >
                {product.featured && (
                  <span className="mb-3 inline-block self-start rounded bg-accent px-2 py-0.5 text-xs font-semibold text-white">
                    Featured
                  </span>
                )}
                <h3 className="text-brand">{product.title}</h3>
                <p className="mt-2 text-sm text-body">{product.description}</p>
                <Link
                  href={product.href}
                  className="mt-auto pt-5 text-sm font-semibold text-brand hover:underline"
                >
                  Learn more &rarr;
                </Link>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}