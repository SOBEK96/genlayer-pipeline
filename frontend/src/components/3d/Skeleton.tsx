import { clsx } from "@/lib/cx";

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("skeleton h-4 w-full", className)} />;
}

/** Immersive card skeleton used during on-chain / consensus waits. */
export function SkeletonCard() {
  return (
    <div className="glass space-y-4 p-5">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-xl" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3 w-1/3" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <Skeleton className="h-8 w-2/3" />
      <div className="grid grid-cols-3 gap-3">
        <Skeleton className="h-14" />
        <Skeleton className="h-14" />
        <Skeleton className="h-14" />
      </div>
    </div>
  );
}

export function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 py-3">
      <Skeleton className="h-8 w-8 rounded-lg" />
      <Skeleton className="h-3 w-40" />
      <Skeleton className="ml-auto h-3 w-24" />
    </div>
  );
}
