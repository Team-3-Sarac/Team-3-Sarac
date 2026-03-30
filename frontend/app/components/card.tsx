export default function Card({ className = "", children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      className={`rounded-xl border border-white/[0.07] bg-[#0f0f0f] ${className}`}
    >
      {children}
    </div>
  );
}