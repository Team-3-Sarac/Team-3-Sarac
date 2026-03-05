export default function CardHeader({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-neutral-800 px-5 py-4">
      <div>
        <div className="text-sm font-semibold">{title}</div>
        {subtitle ? <div className="text-xs text-neutral-400">{subtitle}</div> : null}
      </div>
      {right ? <div className="pt-1">{right}</div> : null}
    </div>
  );
}