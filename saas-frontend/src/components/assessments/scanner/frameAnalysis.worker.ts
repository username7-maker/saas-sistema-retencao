import { analyzeDocumentFrame, type FrameSignature } from "./frameAnalysis";
import type { AnalysisRequest, AnalysisResponse } from "./analysisProtocol";

let previous: FrameSignature | null = null;
let session: number | null = null;
self.onmessage = ({ data }: MessageEvent<AnalysisRequest>) => {
  const { sessionId, requestId, image } = data;
  if (session !== sessionId) { previous = null; session = sessionId; }
  let response: AnalysisResponse;
  try {
    const result = analyzeDocumentFrame(image, previous);
    previous = result.signature;
    response = { sessionId, requestId, result };
  } catch {
    previous = null;
    response = { sessionId, requestId, error: "analysis_failed" };
  }
  self.postMessage(response);
};
