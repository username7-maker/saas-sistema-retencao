export function stopMediaStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
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
