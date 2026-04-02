import Badge from "./badge";

type ClaimRowProps = {
  text: string;
  category?: string | null;
  sentiment?: string | null;
  mentions?: number;
};

function getCategoryLabel(category?: string | null): string {
  if (!category) return "General";
  const labels: Record<string, string> = {
    transfers: "Transfers",
    injuries: "Injuries",
    tactics: "Tactics",
    controversy: "Controversy",
    other: "General",
  };
  return labels[category] || category.charAt(0).toUpperCase() + category.slice(1);
}

function getSentimentColor(sentiment?: string | null): string {
  switch (sentiment) {
    case "positive":
      return "text-emerald-400";
    case "negative":
      return "text-red-400";
    case "neutral":
      return "text-neutral-400";
    default:
      return "text-neutral-500";
  }
}

function getSentimentBadge(sentiment?: string | null): "pos" | "neu" | "neg" {
  switch (sentiment) {
    case "positive":
      return "pos";
    case "negative":
      return "neg";
    default:
      return "neu";
  }
}

export default function ClaimRow({ text, category, sentiment, mentions }: ClaimRowProps) {
  return (
    <div className="px-6 py-4 hover:bg-[#161616] transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-[13px] text-neutral-300 line-clamp-2 leading-relaxed">
            {text}
          </p>
          <div className="flex items-center gap-3 mt-2">
            <Badge tone="neutral">{getCategoryLabel(category)}</Badge>
            {sentiment && (
              <span className={`text-[11px] font-medium ${getSentimentColor(sentiment)}`}>
                {sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}
              </span>
            )}
            {mentions !== undefined && mentions > 0 && (
              <span className="text-[11px] text-neutral-500">
                {mentions} mention{mentions !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>
        <div className="shrink-0">
          <Badge tone={getSentimentBadge(sentiment)}>
            {sentiment ? getSentimentLabel(sentiment) : "Neutral"}
          </Badge>
        </div>
      </div>
    </div>
  );
}

function getSentimentLabel(sentiment: string): string {
  switch (sentiment) {
    case "positive":
      return "Positive";
    case "negative":
      return "Negative";
    default:
      return "Neutral";
  }
}
