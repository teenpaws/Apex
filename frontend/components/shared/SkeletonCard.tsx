import { cn } from '@/lib/utils';

interface SkeletonCardProps {
  lines?: number;
  className?: string;
}

export function SkeletonCard({ lines = 3, className }: SkeletonCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card p-5 space-y-3 animate-pulse',
        className
      )}
      aria-busy="true"
      aria-label="Loading..."
    >
      {/* Header bar */}
      <div className="h-3 w-1/3 rounded-full bg-muted" />
      {/* Content lines */}
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={cn(
            'h-2.5 rounded-full bg-muted',
            i === lines - 1 ? 'w-2/3' : 'w-full'
          )}
        />
      ))}
    </div>
  );
}
