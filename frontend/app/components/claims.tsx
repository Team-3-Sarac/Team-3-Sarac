export default function ClaimsPanel() {
  const claims = [
    {
      claim: "Arsenal are the strongest title contenders this season.",
      confidence: 88,
      sentiment: "positive",
      mentions: 126,
      leagues: ["Premier League"],
    },
    {
      claim: "VAR decisions are having too much influence on match results.",
      confidence: 82,
      sentiment: "negative",
      mentions: 94,
      leagues: ["Premier League", "La Liga", "Serie A"],
    },
    {
      claim: "Real Madrid have more depth than Barcelona this season.",
      confidence: 79,
      sentiment: "neutral",
      mentions: 73,
      leagues: ["La Liga"],
    },
    {
      claim: "Kane has completely transformed Bayern’s attack.",
      confidence: 91,
      sentiment: "positive",
      mentions: 68,
      leagues: ["Bundesliga"],
    },
    {
      claim: "Injuries are hurting Napoli’s title chances.",
      confidence: 76,
      sentiment: "negative",
      mentions: 52,
      leagues: ["Serie A"],
    },
  ];

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-950/40 shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
      <div className="border-b border-neutral-800 px-5 py-4">
        <div className="text-sm font-semibold">Emerging Claims</div>
        <div className="text-xs text-neutral-400">
          Repeated claims and narratives extracted from soccer video coverage
        </div>
      </div>

      <div className="divide-y divide-neutral-800">
        {claims.map((item, index) => (
          <div key={index} className="px-5 py-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-white">{item.claim}</p>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <ClaimBadge label={`${item.mentions} mentions`} tone="neutral" />
                  <ClaimBadge
                    label={`${item.confidence}% confidence`}
                    tone="blue"
                  />
                  <ClaimBadge
                    label={item.sentiment}
                    tone={
                      item.sentiment === "positive"
                        ? "green"
                        : item.sentiment === "negative"
                        ? "red"
                        : "yellow"
                    }
                  />
                  {item.leagues.map((league) => (
                    <ClaimBadge key={league} label={league} tone="neutral" />
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ClaimBadge({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "neutral" | "green" | "red" | "yellow" | "blue";
}) {
  const styles = {
    neutral: "border-neutral-800 bg-neutral-900/50 text-neutral-300",
    green: "border-emerald-500/20 bg-emerald-500/10 text-emerald-300",
    red: "border-red-500/20 bg-red-500/10 text-red-300",
    yellow: "border-amber-500/20 bg-amber-500/10 text-amber-300",
    blue: "border-sky-500/20 bg-sky-500/10 text-sky-300",
  };

  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-1 text-[11px] ${styles[tone]}`}
    >
      {label}
    </span>
  );
}