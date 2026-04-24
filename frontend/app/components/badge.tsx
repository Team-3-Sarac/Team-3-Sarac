export default function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "pos" | "neu" | "neg" | "teal" | "sky" | "hot" | "active" | "paused";
}) {
  const cls = {
    pos:     "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    neu:     "bg-amber-500/10 text-amber-300 border-amber-500/20",
    neg:     "bg-red-500/10 text-red-300 border-red-500/20",
    teal:    "bg-teal-500/10 text-teal-300 border-teal-500/20",
    sky:     "bg-sky-500/10 text-sky-300 border-sky-500/20",
    hot:     "bg-orange-500/10 text-orange-300 border-orange-500/20",
    active:  "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    paused:  "bg-neutral-500/10 text-neutral-400 border-neutral-500/20",
    neutral: "bg-white/[0.05] text-neutral-300 border-white/[0.08]",
  }[tone];
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${cls}`}>
      {children}
    </span>
  );
}