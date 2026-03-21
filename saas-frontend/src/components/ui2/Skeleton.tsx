import { cn } from "./cn";

type SkeletonProps = React.HTMLAttributes<HTMLDivElement>;

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded bg-[linear-gradient(90deg,hsl(var(--lovable-border)/0.55),hsl(var(--lovable-border-strong)/0.35),hsl(var(--lovable-border)/0.55))] bg-[length:200%_100%]",
        className,
      )}
      {...props}
    />
  );
}
