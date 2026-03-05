export default function EventRow({ icon, title, time }: { icon: React.ReactNode; title: string; time: string }) {
  return (
    <div className="flex gap-3 px-5 py-4">
      <div className="mt-0.5">{icon}</div>
      <div className="min-w-0">
        <div className="truncate text-sm font-medium">{title}</div>
        <div className="text-xs text-neutral-500">{time}</div>
      </div>
    </div>
  );
}