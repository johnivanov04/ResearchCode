export const site = {
  name: "ResearchCode",
  tagline: "Build research software with AI. Trust the results.",
  description:
    "Open-source guides and a starter toolkit that help researchers use AI coding assistants to build correct, maintainable, reproducible scientific software.",
  context: "A Caltech CS/EE 143 special project",
  repository: "https://github.com/johnivanov04/ResearchCode",
} as const;

export type NavItem = {
  href: string;
  label: string;
};

/** Primary navigation. Order here is the order shown in the header. */
export const primaryNav: readonly NavItem[] = [
  { href: "/guides", label: "Guides" },
  { href: "/starter-kit", label: "Starter Kit" },
  { href: "/example", label: "Example" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/about", label: "About" },
];

/** Returns true when `href` is the current page or an ancestor section of it. */
export function isActivePath(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
