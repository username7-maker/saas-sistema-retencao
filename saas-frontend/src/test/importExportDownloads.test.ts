import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../services/api";
import { importExportService } from "../services/importExportService";
vi.mock("../services/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });
describe("spreadsheet download", () => {
  it("keeps the URL available until the browser consumes it and then releases it", async () => {
    vi.useFakeTimers();
    const blob = new Blob(["full_name\nAluno"], { type: "text/csv" });
    vi.mocked(api.get).mockResolvedValue({ data: blob, headers: { "content-disposition": 'attachment; filename="members.csv"' } });
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:csv");
    const release = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe("members.csv");
      expect(this.isConnected).toBe(true);
      expect(release).not.toHaveBeenCalled();
    });
    await importExportService.exportMembersCsv();
    expect(click).toHaveBeenCalledOnce();
    expect(release).not.toHaveBeenCalled();
    expect(api.get).toHaveBeenCalledWith("/api/v1/exports/members.csv", { responseType: "blob", timeout: 120000 });
    vi.advanceTimersByTime(60000);
    expect(release).toHaveBeenCalledWith("blob:csv");
  });
  it("does not download an error response", async () => {
    vi.mocked(api.get).mockRejectedValue(new Error("export failed"));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    await expect(importExportService.exportCheckinsCsv("2026-10-01", "2026-10-06")).rejects.toThrow("export failed");
    expect(click).not.toHaveBeenCalled();
    expect(api.get).toHaveBeenCalledWith("/api/v1/exports/checkins.csv?date_from=2026-10-01&date_to=2026-10-06", { responseType: "blob", timeout: 120000 });
  });
});


describe("daily import acknowledgement", () => {
  it("sends the exact confirmed pending dates alongside the file", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { imported: 1 } });
    const file = new File(["data,hora\n2026-10-13,08:00"], "Acessos.csv");
    await importExportService.importCheckins(file, false, undefined, ["2026-10-12"]);
    const [url, body, options] = vi.mocked(api.post).mock.calls[vi.mocked(api.post).mock.calls.length - 1];
    expect(url).toBe("/api/v1/imports/checkins");
    expect((body as FormData).get("acknowledged_pending_dates")).toBe('["2026-10-12"]');
    expect((body as FormData).get("file")).toBe(file);
    expect(options?.timeout).toBe(600000);
  });
});
