export default function CardHeader({
  title,
  subtitle,
  right,
  legendItems,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  legendItems?: { color: string; label: string }[];
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-white/6 px-6 py-5">
      <div>
        <div
          className="text-[15px] font-semibold text-white"
          style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
        >
          {title}
        </div>
        {(subtitle || legendItems) && (
          <div className="mt-1 flex items-center gap-4">
            {subtitle && <span className="text-xs text-neutral-500">{subtitle}</span>}
            {legendItems && (
              <div className="flex items-center gap-3">
                {legendItems.map((item) => (
                  <span key={item.label} className="flex items-center gap-1.5 text-[11px] text-neutral-500">
                    <span className={`h-1.5 w-1.5 rounded-full ${item.color}`} />
                    {item.label}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}