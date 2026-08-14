"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { CHAPTERS } from "../lib/site";

function isCurrent(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/" || pathname === "";
  }
  return pathname === href || pathname === href.replace(/\/$/, "");
}

export function ChapterNav() {
  const pathname = usePathname();
  return (
    <nav className="chapter-list" aria-label="Strata">
      <p className="spine-mark">FRB</p>
      <p className="spine-title">Stratum field</p>
      <ol>
        {CHAPTERS.map((chapter) => (
          <li
            key={chapter.id}
            className={isCurrent(pathname, chapter.href) ? "is-current" : undefined}
          >
            <Link href={chapter.href}>
              <span className="plate-no">{chapter.roman}</span> {chapter.label}
            </Link>
          </li>
        ))}
      </ol>
      <p className="spine-foot">epoch field</p>
    </nav>
  );
}
