import { describe, expect, it } from "vitest";

import {
  cameraPreferenceScore,
  preferredCamera,
  scannerPreviewAspect,
} from "../components/assessments/GuidedDocumentScanner";

function camera(deviceId: string, label: string): MediaDeviceInfo {
  return { deviceId, label, kind: "videoinput", groupId: "group", toJSON: () => ({}) } as MediaDeviceInfo;
}

describe("GuidedDocumentScanner camera selection", () => {
  it("prefers the main rear camera over ultra-wide and virtual cameras", () => {
    const ultra = camera("ultra", "Camera Ultra-Angular Traseira");
    const main = camera("main", "Camera Principal Traseira");
    const virtual = camera("obs", "OBS Virtual Camera");
    expect(preferredCamera([ultra, virtual, main])?.deviceId).toBe("main");
    expect(cameraPreferenceScore(main)).toBeGreaterThan(cameraPreferenceScore(ultra));
    expect(cameraPreferenceScore(ultra)).toBeGreaterThan(cameraPreferenceScore(virtual));
  });

  it("prefers a physical USB webcam over a virtual desktop camera", () => {
    expect(preferredCamera([
      camera("virtual", "OBS Virtual Camera"), camera("usb", "Logitech BRIO USB Webcam"),
    ])?.deviceId).toBe("usb");
  });

  it("uses the real portrait ratio without creating horizontal letterboxing", () => {
    expect(scannerPreviewAspect(1080, 1920, true)).toBe("1080/1920");
    expect(scannerPreviewAspect(0, 0, true)).toBe("9/16");
    expect(scannerPreviewAspect(0, 0, false)).toBe("16/9");
  });
});
