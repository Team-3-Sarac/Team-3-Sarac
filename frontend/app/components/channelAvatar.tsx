export default function ChannelAvatar({ initials }: { initials: string }) {
  return (
    <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-800 bg-gradient-to-br from-neutral-900 to-neutral-950 text-sm font-semibold text-neutral-200">
      {initials}
    </div>
  );
}