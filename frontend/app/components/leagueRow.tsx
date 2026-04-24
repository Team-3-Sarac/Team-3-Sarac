import Badge from "../components/badge";
import ReactCountryFlag from "react-country-flag";
import Image from "next/image";

const LEAGUE_COUNTRY: Record<string, string> = {
  "ENG": "GB-ENG",
  "ESP": "ES",
  "GER": "DE",
  "ITA": "IT",
  "FRA": "FR",
};

export default function LeagueRow({ code, league, count, status }: { code: string; league: string; count: string; status: string }) {
  return (
    <div className="flex items-center justify-between gap-4 px-6 py-6.5 transition-colors hover:bg-[#161616]">
      <div className="flex items-center gap-3 min-w-0">
        <span className="inline-flex h-6 w-9 shrink-0 items-center justify-center rounded-md border border-white/8 bg-white/4 overflow-hidden">
          {code === "UCL" ? (
            <Image
              src="/league-logo.jpg"
              alt="Champions League"
              width={24}
              height={16}
              className="object-contain"
            />
          ) : (
            <ReactCountryFlag
              countryCode={LEAGUE_COUNTRY[code] ?? "UN"}
              svg
              style={{ width: "24px", height: "16px", objectFit: "cover" }}
            />
          )}
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