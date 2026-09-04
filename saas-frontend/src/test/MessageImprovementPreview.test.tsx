import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MessageImprovementPreview } from "../components/common/MessageImprovementPreview";
import { messageComposerService } from "../services/messageComposerService";

vi.mock("../services/messageComposerService", () => ({
  messageComposerService: {
    improve: vi.fn(),
    apply: vi.fn(),
    discard: vi.fn(),
  },
}));

vi.mock("react-hot-toast", () => ({ default: { success: vi.fn(), error: vi.fn() } }));

const preview = {
  request_id: "request-1",
  base_message: "Oi, Ana! Sentimos sua falta.",
  improved_message: "Oi, Ana! Como podemos ajudar você a retomar sua rotina?",
  model: "gpt-test",
  prompt_version: "1.0.0",
  origin: "ai_improved" as const,
  warnings: [],
  status: "previewed" as const,
  created_at: "2026-09-04T12:00:00Z",
};

describe("MessageImprovementPreview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(messageComposerService.improve).mockResolvedValue(preview);
    vi.mocked(messageComposerService.apply).mockResolvedValue({ ...preview, status: "applied" });
    vi.mocked(messageComposerService.discard).mockResolvedValue({ ...preview, status: "discarded" });
  });

  it("requests AI only after the explicit button and previews before applying", async () => {
    const onApplied = vi.fn();
    render(
      <MessageImprovementPreview
        sourceType="task"
        sourceId="task-1"
        templateKey="retention.reengagement"
        objective="Retomar rotina"
        baseMessage={preview.base_message}
        onApplied={onApplied}
      />,
    );

    expect(messageComposerService.improve).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Melhorar com IA/i }));

    expect(await screen.findByText("Comparar versões")).toBeInTheDocument();
    expect(screen.getByText(preview.improved_message)).toBeInTheDocument();
    expect(onApplied).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Aplicar" }));
    await waitFor(() => expect(onApplied).toHaveBeenCalledWith(preview.improved_message));
  });

  it("discards without applying or sending", async () => {
    const onApplied = vi.fn();
    render(
      <MessageImprovementPreview
        sourceType="task"
        sourceId="task-1"
        templateKey="retention.reengagement"
        objective="Retomar rotina"
        baseMessage={preview.base_message}
        onApplied={onApplied}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Melhorar com IA/i }));
    await screen.findByText("Comparar versões");
    fireEvent.click(screen.getByRole("button", { name: "Descartar" }));
    await waitFor(() => expect(messageComposerService.discard).toHaveBeenCalledWith("request-1"));
    expect(onApplied).not.toHaveBeenCalled();
  });
});
