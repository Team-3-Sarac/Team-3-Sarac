import Badge from "../components/badge";

export default function LeagueRow({ code, league, count, status }: { code: string; league: string; count: string; status: string }) {
  return (
    <div className="flex items-center justify-between gap-4 px-6 py-4 transition-colors hover:bg-[#161616]">
      <div className="flex items-center gap-3 min-w-0">
        <span className="inline-flex h-6 w-9 shrink-0 items-center justify-center rounded-md border border-white/8 bg-white/4 text-[10px] font-semibold text-neutral-400 tracking-wider">
          {code}
        </span>
        <span className="truncate text-[13px] font-medium text-white/80">
          {league}
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <span className="text-[11px] text-neutral-500 tabular-nums">{count} videos</span>
        {status && <Badge tone="teal">{status}</Badge>}
      </div>
    </div>
  );
}