import Pill from "../components/pill";
import Sentiment from "../components/sentiment";
import ChannelAvatar from "../components/channelAvatar";
import Toggle from "../components/toggle";

type Channel = {
  id: string;
  initials: string;
  name: string;
  handle: string;
  subs: string;
  league: string;
  videos: number;
  sentimentPct: number;
  sentimentDir: "up" | "down" | "flat";
  latestTitle: string;
  latestViews: string;
  active: boolean;
};

export default function ChannelRow({
  row,
  onToggle,
}: {
  row: Channel;
  onToggle: () => void;
}) {
  return (
    <div className="grid grid-cols-12 items-center gap-4 px-5 py-4">
      {/* Channel */}
      <div className="col-span-4 flex items-center gap-3 min-w-0">
        <ChannelAvatar initials={row.initials} />
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">{row.name}</div>
          <div className="mt-0.5 flex items-center gap-2 text-xs text-neutral-500">
            <span className="truncate">{row.handle}</span>
            <span className="text-neutral-700">•</span>
            <span className="shrink-0">{row.subs}</span>
          </div>
        </div>
      </div>

      {/* League */}
      <div className="col-span-2">
        <Pill>{row.league}</Pill>
      </div>

      {/* Videos */}
      <div className="col-span-1 text-right text-sm font-semibold">{row.videos}</div>

      {/* Sentiment */}
      <div className="col-span-1 text-right text-sm">
        <Sentiment pct={row.sentimentPct} dir={row.sentimentDir} />
      </div>

      {/* Latest */}
      <div className="col-span-3 min-w-0">
        <div className="flex items-start gap-2">
          <span className="mt-0.5 text-neutral-600">▷</span>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">{row.latestTitle}</div>
            <div className="mt-1 text-xs text-neutral-500">{row.latestViews}</div>
          </div>
        </div>
      </div>

      {/* Active */}
      <div className="col-span-1 flex justify-end">
        <Toggle on={row.active} onClick={onToggle} />
      </div>
    </div>
  );
}