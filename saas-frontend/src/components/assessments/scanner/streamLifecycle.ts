export function stopMediaStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}

export function requestMediaStreamWithTimeout(
  request: () => Promise<MediaStream>,
  timeoutMs: number,
): Promise<MediaStream> {
  return new Promise((resolve, reject) => {
    let settled = false;
    const timer = window.setTimeout(() => {
      settled = true;
      reject(new Error("camera_request_timeout"));
    }, timeoutMs);

    request().then((stream) => {
      if (settled) {
        stopMediaStream(stream);
        return;
      }
      settled = true;
      window.clearTimeout(timer);
      resolve(stream);
    }, (error: unknown) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      reject(error);
    });
  });
}

export class CameraAttemptController {
  private generation = 0;
  active: MediaStream | null = null;

  begin(): number {
    this.generation += 1;
    stopMediaStream(this.active);
    this.active = null;
    return this.generation;
  }

  isCurrent(attempt: number): boolean {
    return attempt === this.generation;
  }

  accept(attempt: number, stream: MediaStream): boolean {
    if (!this.isCurrent(attempt)) {
      stopMediaStream(stream);
      return false;
    }
    stopMediaStream(this.active);
    this.active = stream;
    return true;
  }

  invalidate(): void {
    this.generation += 1;
    stopMediaStream(this.active);
    this.active = null;
  }
}
