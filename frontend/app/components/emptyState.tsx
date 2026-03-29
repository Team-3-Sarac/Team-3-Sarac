export default function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-40 items-center justify-center text-sm text-neutral-600">
      {message}
    </div>
  );
}