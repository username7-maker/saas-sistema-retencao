import { cn } from "../cn";

interface PremiumSkeletonProps {
  className?: string;
  rows?: number;
}

export function PremiumSkeleton({ className, rows }: PremiumSkeletonProps) {
  if (rows && rows > 1) {
    return (
      <div className={cn("space-y-3", className)}>
        {Array.from({ length: rows }, (_, index) => (
          <div key={index} className="command-skeleton h-14 rounded-2xl" />
        ))}
      </div>
    );
  }

  return <div className={cn("command-skeleton rounded-2xl", className)} />;
}
