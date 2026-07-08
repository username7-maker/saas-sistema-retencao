export type SlotStatus =
  | 'available'
  | { kind: 'claimed'; worker: string }
  | { kind: 'done'; worker?: string }
  | { kind: 'blocked'; reason?: string }
  | { kind: 'unknown'; raw: string };

export interface Slot {
  id: string;                  // ex: "tool-parse-datetime"
  milestone: string;           // ex: "M1"
  path: string;                // absolute path to specs/slots/<m>/<id>/
  status: SlotStatus;
  owner: string | null;        // do OWNER.txt
  hasBrief: boolean;
  hasContract: boolean;
  hasArtifacts: boolean;
}

export interface Worktree {
  name: string;                // ex: "worker-A"
  path: string;                // absolute
  branch: string;
  head: string;                // sha curto
}

export interface WorkerBranch {
  branch: string;              // ex: "worker/M1/tool-X"
  milestone: string;
  slotId: string;
  worker: string;              // ex: "worker-A"
  status: SlotStatus;
  owner: string | null;
}
