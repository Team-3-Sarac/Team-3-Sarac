export default function LeagueRow({ code, league, count, status }: { code: string; league: string; count: string; status: string }) {
  return (
    <div className="flex items-center justify-between gap-4 px-5 py-4">
      <div className="flex items-center gap-3 min-w-0">
        <span className="inline-flex h-7 w-9 items-center justify-center rounded-md bg-neutral-900 text-[10px] text-neutral-200 border border-neutral-800">
          {code}
        </span>
        <div className="truncate text-sm font-medium">{league}</div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <div className="text-xs text-neutral-500">{count}</div>
        {status ? (
          <span className="rounded-md bg-sky-500/15 px-2 py-1 text-[11px] text-sky-300 border border-sky-500/20">
            {status}
          </span>
        ) : null}
      </div>
    </div>
  );
}