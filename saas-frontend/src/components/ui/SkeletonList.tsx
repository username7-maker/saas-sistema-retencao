import { cn } from "../ui2";

interface SkeletonListProps {
  rows?: number;
  cols?: number;
}

const FLEX_PATTERN = ["flex-[1]", "flex-[2]", "flex-[1]"];
const WIDTH_PATTERN = ["w-4/5", "w-full", "w-3/4", "w-5/6"];

export function SkeletonList({ rows = 5, cols = 3 }: SkeletonListProps) {
  return (
    <div className="space-y-0">
      {Array.from({ length: rows }, (_, rowIndex) => (
        <div key={rowIndex} className="flex items-center gap-4 border-b border-lovable-border/55 py-3">
          {Array.from({ length: cols }, (_, colIndex) => (
            <div key={colIndex} className={cn("min-w-0", FLEX_PATTERN[colIndex % FLEX_PATTERN.length])}>
              {/* command-skeleton uses the branded directional shimmer from index.css */}
              <div className={cn("command-skeleton h-4 rounded-md", WIDTH_PATTERN[(rowIndex + colIndex) % WIDTH_PATTERN.length])} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
