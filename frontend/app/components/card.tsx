export default function Card({ className = "", children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={`rounded-2xl border border-neutral-800 bg-neutral-950/40 shadow-[0_0_0_1px_rgba(255,255,255,0.03)] ${className}`}>
      {children}
    </div>
  );
}
