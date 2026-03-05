export default function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-md border border-neutral-800 bg-neutral-900/40 px-2 py-1 text-[11px] text-neutral-200">
      {children}
    </span>
  );
}
