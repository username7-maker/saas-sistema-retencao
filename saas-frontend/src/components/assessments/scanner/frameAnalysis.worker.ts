import { analyzeDocumentFrame, type FrameSignature } from "./frameAnalysis";

let previous: FrameSignature | null = null;
self.onmessage = (event: MessageEvent<ImageData>) => {
  const result = analyzeDocumentFrame(event.data, previous);
  previous = result.signature;
  self.postMessage(result);
};
