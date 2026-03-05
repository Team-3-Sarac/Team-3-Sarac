export default function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "pos" | "neu" | "neg" }) {
  const cls =
    tone === "pos"
      ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/20"
      : tone === "neu"
      ? "bg-amber-500/15 text-amber-300 border-amber-500/20"
      : tone === "neg"
      ? "bg-red-500/15 text-red-300 border-red-500/20"
      : "bg-neutral-800/40 text-neutral-200 border-neutral-700";

  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] ${cls}`}>
      {children}
    </span>
  );
}