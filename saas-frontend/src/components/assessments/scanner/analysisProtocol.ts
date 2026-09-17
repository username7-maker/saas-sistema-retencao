import type { FrameAnalysis } from "./frameAnalysis";

export type AnalysisRequest = { sessionId: number; requestId: number; image: ImageData };
export type AnalysisResponse = { sessionId: number; requestId: number } & (
  | { result: FrameAnalysis; error?: never }
  | { error: "analysis_failed"; result?: never }
);
