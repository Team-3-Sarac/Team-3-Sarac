import Card from "../components/card";
import Skeleton from "../components/skeleton";

export default function KpiCard({
  title,
  value,
  sub,
  icon,
  loading,
}: {
  title: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  loading: boolean;
}) {
  return (
      <Card className="flex flex-col gap-3 p-6">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-neutral-500">
            {title}
          </span>
          <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/[0.07] bg-white/4 text-neutral-400">
            {icon}
          </div>
        </div>
        {loading ? (
          <>
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-3 w-32" />
          </>
        ) : (
          <>
            <div
              className="text-[2rem] font-black leading-none tracking-tight text-white"
              style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
            >
              {value}
            </div>
            <div className="text-xs text-emerald-400">{sub}</div>
          </>
        )}
      </Card>
    );
  }