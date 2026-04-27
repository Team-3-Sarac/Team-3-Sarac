import {
  Play,
  Clock,
  ChevronRight,
  Eye,
  ThumbsUp,
  MessageSquare,
} from "lucide-react";
import Badge from "../components/badge";

export default function VideoRow({
  videoId,
  league,
  teams,
  sentiment,
  sentimentTone,
  title,
  channel,
  duration,
  views,
  likes,
  comments,
  age,
}: {
  videoId: string;
  league: string;
  teams: string[];
  sentiment: string;
  sentimentTone: "pos" | "neu" | "neg";
  title: string;
  channel: string;
  duration: string;
  views: string;
  likes: string;
  comments: string;
  age: string;
}) {
  return (
    <div
      className="group flex cursor-pointer gap-4 px-6 py-4 transition-colors hover:bg-[#161616]"
      onClick={() =>
        window.open(`https://youtube.com/watch?v=${videoId}`, "_blank")
      }
    >
      {/* Thumbnail */}
      <div className="relative h-18 w-32 shrink-0 overflow-hidden rounded-lg border border-white/[0.07] bg-neutral-900">
        <img
          src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
          alt={title}
          className="h-full w-full object-cover opacity-90 transition-opacity group-hover:opacity-100"
          loading="lazy"
        />
        {/* play overlay */}
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition-opacity group-hover:opacity-100">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white/90">
            <Play className="h-3.5 w-3.5 fill-black text-black" />
          </div>
        </div>
        <div className="absolute bottom-1.5 right-1.5 rounded bg-black/75 px-1.5 py-0.5 text-[10px] font-medium text-white">
          {duration}
        </div>
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          {sentiment !== "N/A" && <Badge tone={sentimentTone}>{sentiment}</Badge>}
          {teams.slice(0, 2).map((team) => (
            <Badge key={team} tone="neutral">{team}</Badge>
          ))}
        </div>
        <div className="mt-2 line-clamp-1 text-[13px] font-semibold leading-snug text-white group-hover:text-teal-300 transition-colors">
          {title}
        </div>
        <div className="mt-0.5 text-xs text-neutral-500">{channel}</div>
        <div className="mt-2.5 flex flex-wrap items-center gap-3.5 text-[11px] text-neutral-600">
          <span className="inline-flex items-center gap-1">
            <Eye className="h-3 w-3" /> {views}
          </span>
          <span className="inline-flex items-center gap-1">
            <ThumbsUp className="h-3 w-3" /> {likes}
          </span>
          <span className="inline-flex items-center gap-1">
            <MessageSquare className="h-3 w-3" /> {comments}
          </span>
          <span className="inline-flex items-center gap-1 ml-auto">
            <Clock className="h-3 w-3" /> {age}
          </span>
        </div>
      </div>

      {/* Arrow */}
      <div className="flex items-center opacity-0 transition-opacity group-hover:opacity-100">
        <ChevronRight className="h-4 w-4 text-neutral-500" />
      </div>
    </div>
  );
}