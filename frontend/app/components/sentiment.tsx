export default function Sentiment({
  pct,
  dir,
}: {
  pct: number;
  dir: "up" | "down" | "flat";
}) {
  const cls =
    pct >= 70 ? "text-emerald-400" : pct >= 60 ? "text-sky-400" : pct >= 50 ? "text-amber-400" : "text-red-400";

  const arrow =
    dir === "up" ? "↗" : dir === "down" ? "↘" : "–";

  return (
    <span className={`inline-flex items-center justify-end gap-2 font-semibold ${cls}`}>
      <span className="text-neutral-500">{arrow}</span>
      {pct}%
    </span>
  );
}