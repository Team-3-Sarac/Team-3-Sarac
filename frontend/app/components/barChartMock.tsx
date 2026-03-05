export default function BarChartMock() {
  const bars = [
    { label: "PL", value: 420 },
    { label: "La Liga", value: 290 },
    { label: "BL", value: 200 },
    { label: "Serie A", value: 190 },
    { label: "Ligue 1", value: 160 },
  ];

  const max = Math.max(...bars.map((b) => b.value));

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950 p-4">
      <div className="relative h-56">
        {/* grid */}
        <div className="absolute inset-0 opacity-60">
          <div className="h-full w-full bg-[linear-gradient(to_right,rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-[size:56px_56px]" />
        </div>

        {/* bars */}
        <div className="absolute inset-0 flex items-end justify-between gap-5 px-3 pb-6">
          {bars.map((b) => (
            <div key={b.label} className="flex w-full flex-col items-center gap-2">
              <div
                className="w-full rounded-md bg-sky-500"
                style={{ height: `${(b.value / max) * 100}%` }}
              />
              <div className="text-[11px] text-neutral-400">{b.label}</div>
            </div>
          ))}
        </div>

        {/* y labels */}
        <div className="absolute left-2 top-2 flex h-[calc(100%-28px)] flex-col justify-between text-[11px] text-neutral-500">
          <span>600</span>
          <span>450</span>
          <span>300</span>
          <span>150</span>
          <span>0</span>
        </div>
      </div>
    </div>
  );
}