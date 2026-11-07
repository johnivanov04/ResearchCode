import Link from "next/link";
import { LogoMark } from "@/components/logo";
import { SiteNav } from "@/components/site-nav";
import { site } from "@/content/site";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/85">
      <div className="relative mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded-md text-ink"
          aria-label={`${site.name} home`}
        >
          <LogoMark />
          <span className="text-[1.05rem] font-semibold tracking-tight">{site.name}</span>
        </Link>
        <SiteNav />
      </div>
    </header>
  );
}
