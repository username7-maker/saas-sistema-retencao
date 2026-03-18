import { Inbox, SearchX } from "lucide-react";

import { Button, Card, CardContent } from "../ui2";

interface TasksEmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  mode?: "empty" | "search";
}

export function TasksEmptyState({
  title,
  description,
  actionLabel,
  onAction,
  mode = "empty",
}: TasksEmptyStateProps) {
  const Icon = mode === "search" ? SearchX : Inbox;

  return (
    <Card>
      <CardContent className="py-12 text-center">
        <Icon size={28} className="mx-auto text-lovable-ink-muted/30" />
        <h3 className="mt-4 text-base font-semibold text-lovable-ink">{title}</h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-lovable-ink-muted">{description}</p>
        {actionLabel && onAction ? (
          <div className="mt-5">
            <Button size="sm" variant="secondary" onClick={onAction}>
              {actionLabel}
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
