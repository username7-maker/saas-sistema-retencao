import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GuidedDocumentScanner } from "../components/assessments/GuidedDocumentScanner";

function setMediaDevices(getUserMedia: ReturnType<typeof vi.fn>) {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia,
      enumerateDevices: vi.fn().mockResolvedValue([]),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    },
  });
}

describe("GuidedDocumentScanner UI lifecycle", () => {
  afterEach(() => vi.restoreAllMocks());

  it("replaces the preparing state with retry and gallery actions after a camera error", async () => {
    setMediaDevices(vi.fn().mockRejectedValue(new Error("permission denied")));
    render(<GuidedDocumentScanner memberId="member-1" open onClose={vi.fn()} onConfirm={vi.fn()} />);

    expect(await screen.findByText("Tentar novamente")).toBeInTheDocument();
    expect(screen.getAllByText("Escolher da galeria").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Camera indisponivel" })).toBeDisabled();
  });

  it("stops a stream that resolves after the modal was closed", async () => {
    let resolveStream!: (stream: MediaStream) => void;
    const stop = vi.fn();
    const delayed = new Promise<MediaStream>((resolve) => { resolveStream = resolve; });
    setMediaDevices(vi.fn().mockReturnValue(delayed));
    const onClose = vi.fn();
    render(<GuidedDocumentScanner memberId="member-1" open onClose={onClose} onConfirm={vi.fn()} />);

    fireEvent.click(screen.getByLabelText("Fechar camera"));
    resolveStream({ getTracks: () => [{ stop }], getVideoTracks: () => [] } as unknown as MediaStream);

    await waitFor(() => expect(stop).toHaveBeenCalledOnce());
    expect(onClose).toHaveBeenCalledOnce();
  });
});
