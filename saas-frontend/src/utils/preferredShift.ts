export type PreferredShiftKey = "morning" | "afternoon" | "evening";

function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export function getPreferredShiftKey(value: string | null | undefined): PreferredShiftKey | null {
  const normalized = normalizeText(value ?? "");
  if (!normalized) return null;
  if (["morning", "manha", "matutino"].includes(normalized)) return "morning";
  if (["afternoon", "tarde", "vespertino"].includes(normalized)) return "afternoon";
  if (["evening", "night", "noite", "noturno"].includes(normalized)) return "evening";
  return null;
}

export function getPreferredShiftLabel(value: string | null | undefined): string | null {
  const key = getPreferredShiftKey(value);
  if (key === "morning") return "Manha";
  if (key === "afternoon") return "Tarde";
  if (key === "evening") return "Noite";
  const raw = (value ?? "").trim();
  if (!raw) return null;
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

export function matchesPreferredShift(value: string | null | undefined, filter: PreferredShiftKey | "all"): boolean {
  if (filter === "all") return true;
  return getPreferredShiftKey(value) === filter;
}

