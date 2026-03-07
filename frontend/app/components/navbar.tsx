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
    <header className="sticky top-0 z-50 w-full border-b border-neutral-800 bg-black/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-3">
          <div className="relative h-9 w-9 overflow-hidden rounded-lg border border-neutral-800 bg-neutral-900">
            <Image
              src="/MatchIQ.png"
              alt="Logo"
              fill
              className="object-cover"
              priority
            />
          </div>
          <span className="text-sm font-semibold tracking-wide text-white">
            MatchIQ
          </span>
        </Link>

        <nav className="flex items-center gap-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={[
                  "rounded-md px-4 py-2 text-sm font-medium transition",
                  isActive
                    ? "bg-white text-black"
                    : "text-neutral-300 hover:bg-neutral-900 hover:text-white",
                ].join(" ")}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}