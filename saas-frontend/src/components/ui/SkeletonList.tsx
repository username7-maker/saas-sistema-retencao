import { Skeleton, cn } from "../ui2";

interface SkeletonListProps {
  rows?: number;
  cols?: number;
}

function getFlexClass(index: number): string {
  const pattern = ["flex-[1]", "flex-[2]", "flex-[1]"];
  return pattern[index % pattern.length];
}

function getWidthClass(rowIndex: number, colIndex: number): string {
  const pattern = ["w-4/5", "w-full", "w-3/4", "w-5/6"];
  return pattern[(rowIndex + colIndex) % pattern.length];
}

export function SkeletonList({ rows = 5, cols = 3 }: SkeletonListProps) {
  return (
    <div>
      {Array.from({ length: rows }, (_, rowIndex) => (
        <div key={rowIndex} className="flex items-center gap-4 border-b border-lovable-border py-3">
          {Array.from({ length: cols }, (_, colIndex) => (
            <div key={colIndex} className={cn("min-w-0", getFlexClass(colIndex))}>
              <Skeleton className={cn("h-4", getWidthClass(rowIndex, colIndex))} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
