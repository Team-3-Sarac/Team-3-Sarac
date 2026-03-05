export default function LineChartMock() {
  return (
    <div className="relative h-64 overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950 p-4">
      {/* grid */}
      <div className="absolute inset-0 opacity-60">
        <div className="h-full w-full bg-[linear-gradient(to_right,rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-[size:56px_56px]" />
      </div>

      {/* lines */}
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 700 260" preserveAspectRatio="none">
        {/* Transfers (green) */}
        <path
          d="M0,80 C120,120 180,140 260,90 C340,40 380,120 460,140 C560,170 610,120 700,90"
          fill="none"
          stroke="rgb(52 211 153)"
          strokeWidth="2.5"
        />
        {/* Injuries (red) */}
        <path
          d="M0,170 C120,150 190,140 260,170 C330,200 360,120 430,140 C520,165 610,170 700,190"
          fill="none"
          stroke="rgb(248 113 113)"
          strokeWidth="2.5"
        />
        {/* Tactics (blue) */}
        <path
          d="M0,140 C120,160 210,150 280,130 C360,110 420,90 480,100 C580,120 630,110 700,90"
          fill="none"
          stroke="rgb(56 189 248)"
          strokeWidth="2.5"
        />
        {/* Controversy (amber) */}
        <path
          d="M0,190 C140,160 210,140 300,130 C380,120 400,200 480,180 C580,150 640,160 700,140"
          fill="none"
          stroke="rgb(251 191 36)"
          strokeWidth="2.5"
        />
      </svg>

      {/* x labels */}
      <div className="absolute bottom-3 left-0 right-0 flex justify-between px-6 text-[11px] text-neutral-500">
        <span>W1</span>
        <span>W2</span>
        <span>W3</span>
        <span>W4</span>
        <span>W5</span>
        <span>W6</span>
      </div>

      {/* y labels */}
      <div className="absolute left-3 top-3 flex h-[calc(100%-44px)] flex-col justify-between text-[11px] text-neutral-500">
        <span>60</span>
        <span>45</span>
        <span>30</span>
        <span>15</span>
        <span>0</span>
      </div>
    </div>
  );
}