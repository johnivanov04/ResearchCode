import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Page not found",
};

export default function NotFound() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-24 text-center sm:px-6">
      <p className="font-mono text-sm font-medium text-accent-700">404</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">Page not found</h1>
      <p className="mt-4 leading-7 text-body">
        The page you are looking for does not exist or has moved.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link href="/" className="rounded-md bg-navy-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-900">
          Go to the home page
        </Link>
        <Link href="/guides" className="rounded-md border border-line px-5 py-2.5 text-sm font-semibold text-ink hover:border-navy-200">
          Browse the guides
        </Link>
      </div>
    </div>
  );
}
