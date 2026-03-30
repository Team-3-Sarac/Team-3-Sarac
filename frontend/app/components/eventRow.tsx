export default function EventRow({ icon, title, time }: { icon: React.ReactNode; title: string; time: string }) {
  return (
    <div className="flex gap-3 px-6 py-4 transition-colors hover:bg-[#161616]">
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-white/[0.07] bg-white/3">
        {icon}
      </div>
      <div className="min-w-0">
        <div className="line-clamp-2 text-[13px] font-medium leading-snug text-white/80">
          {title}
        </div>
        <div className="mt-0.5 text-[11px] text-neutral-600">{time}</div>
      </div>
    </div>
  );
}