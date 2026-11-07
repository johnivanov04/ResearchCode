import Link from "next/link";
import { LogoMark } from "@/components/logo";
import { primaryNav, site } from "@/content/site";

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-line bg-surface">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.5fr_1fr]">
        <div className="max-w-md">
          <div className="flex items-center gap-2.5 text-ink">
            <LogoMark className="h-6 w-6" />
            <span className="font-semibold tracking-tight">{site.name}</span>
          </div>
          <p className="mt-3 text-sm leading-6 text-muted">
            {site.context}. An open-source educational resource; not an official Caltech
            publication or service.
          </p>
        </div>
        <nav aria-label="Footer">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">Site</h2>
          <ul className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <li>
              <Link href="/" className="text-body hover:text-accent-700">
                Home
              </Link>
            </li>
            {primaryNav.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="text-body hover:text-accent-700">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
