import {
  TrendingUp,
  Video,
  Activity,
  Users,
  ArrowUpRight,
  ArrowDownRight,
  Play,
  Clock,
  Eye,
  ThumbsUp,
  MessageSquare,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import Badge from "../components/badge";

export default function VideoRow({
  league,
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
  league: string;
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
    <div className="flex gap-5 px-5 py-5">
      {/* thumb */}
      <div className="relative h-20 w-36 shrink-0 overflow-hidden rounded-xl border border-neutral-800 bg-gradient-to-br from-neutral-900 to-neutral-950">
        <div className="absolute inset-0 flex items-center justify-center">
          <Play className="h-6 w-6 text-neutral-400" />
        </div>
        <div className="absolute bottom-2 right-2 rounded bg-black/70 px-2 py-0.5 text-[11px] text-neutral-200">
          {duration}
        </div>
      </div>

      {/* content */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral">{league}</Badge>
          <Badge tone={sentimentTone}>{sentiment}</Badge>
        </div>

        <div className="mt-2 truncate text-sm font-semibold">{title}</div>
        <div className="mt-0.5 text-xs text-neutral-500">{channel}</div>

        <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-neutral-500">
          <span className="inline-flex items-center gap-1">
            <Eye className="h-3.5 w-3.5" /> {views}
          </span>
          <span className="inline-flex items-center gap-1">
            <ThumbsUp className="h-3.5 w-3.5" /> {likes}
          </span>
          <span className="inline-flex items-center gap-1">
            <MessageSquare className="h-3.5 w-3.5" /> {comments}
          </span>
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" /> {age}
          </span>
        </div>
      </div>
    </div>
  );
}