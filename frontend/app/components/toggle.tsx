export default function Toggle({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={[
        "relative inline-flex h-6 w-11 items-center rounded-full border transition",
        on ? "bg-white/10 border-neutral-700" : "bg-black border-neutral-800",
      ].join(" ")}
      aria-label="Toggle channel active"
    >
      <span
        className={[
          "inline-block h-5 w-5 transform rounded-full transition",
          on ? "translate-x-5 bg-white" : "translate-x-1 bg-neutral-700",
        ].join(" ")}
      />
    </button>
  );
}
