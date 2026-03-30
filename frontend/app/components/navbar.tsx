"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";

const navItems = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Trends", href: "/trends" },
  { label: "Channels", href: "/channels" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 w-full">
      {/* top accent line */}
      <div className="h-px w-full bg-linear-to-r from-transparent via-teal-500/40 to-transparent" />

      <div className="border-b border-white/6 bg-[#080808]/80 backdrop-blur-2xl">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">

          {/* Logo */}
          <Link
            href="/"
            className="group flex items-center gap-2.5 transition-opacity hover:opacity-80"
          >
            <div className="relative h-8 w-8 overflow-hidden rounded-md border border-white/10 bg-neutral-900 shadow-[0_0_12px_rgba(45,212,191,0.15)]">
              <Image
                src="/MatchIQ.png"
                alt="MatchIQ Logo"
                fill
                className="object-cover"
                priority
              />
            </div>
            <span
              className="text-[22px] font-semibold tracking-[0.04em] text-white/90"
              style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
            >
              Match<span className="text-teal-400">IQ</span>
            </span>
          </Link>

          {/* Nav */}
          <nav className="flex items-center gap-0.5">
            {navItems.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={[
                    "relative rounded-md px-3.5 py-1.5 text-[15px] font-medium tracking-wide transition-all duration-150",
                    isActive
                      ? "text-white"
                      : "text-neutral-400 hover:bg-teal-500/10 hover:text-teal-300",
                  ].join(" ")}
                >
                  {/* Active pill background */}
                  {isActive && (
                    <span className="pointer-events-none absolute inset-0 rounded-md bg-white/[0.07] ring-1 ring-inset ring-white/8" />
                  )}

                  {/* Active bottom dot */}
                  {isActive && (
                    <span className="pointer-events-none absolute bottom-0 left-1/2 h-px w-4 -translate-x-1/2 rounded-full bg-teal-400/80" />
                  )}

                  <span className="relative">{item.label}</span>
                </Link>
              );
            })}
          </nav>

        </div>
      </div>
    </header>
  );
}