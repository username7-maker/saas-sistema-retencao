import { cn } from "../ui2";

interface UserAvatarProps {
  fullName?: string | null;
  avatarUrl?: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeClasses: Record<NonNullable<UserAvatarProps["size"]>, string> = {
  sm: "h-8 w-8 rounded-xl text-xs",
  md: "h-10 w-10 rounded-2xl text-sm",
  lg: "h-14 w-14 rounded-2xl text-base",
};

function getInitials(fullName?: string | null): string {
  return (fullName ?? "AI Gym")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export function UserAvatar({ fullName, avatarUrl, size = "md", className }: UserAvatarProps) {
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={fullName ?? "Avatar do usuário"}
        className={cn(
          "shrink-0 border border-lovable-border/60 object-cover shadow-[0_12px_30px_-18px_hsl(var(--lovable-primary)/0.95)]",
          sizeClasses[size],
          className,
        )}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center bg-[linear-gradient(135deg,hsl(var(--lovable-primary)/0.9),hsl(var(--lovable-info)/0.9))] font-bold text-white shadow-[0_12px_30px_-18px_hsl(var(--lovable-primary)/0.95)]",
        sizeClasses[size],
        className,
      )}
      aria-label={fullName ?? "Avatar do usuário"}
    >
      {getInitials(fullName)}
    </div>
  );
}
