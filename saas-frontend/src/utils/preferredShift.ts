export type PreferredShiftKey = "overnight" | "morning" | "afternoon" | "evening";

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
  if (["overnight", "madrugada", "noturno_madrugada", "plantao_madrugada"].includes(normalized)) return "overnight";
  if (["morning", "manha", "matutino"].includes(normalized)) return "morning";
  if (["afternoon", "tarde", "vespertino"].includes(normalized)) return "afternoon";
  if (["evening", "night", "noite", "noturno"].includes(normalized)) return "evening";
  return null;
}

export function getPreferredShiftLabel(value: string | null | undefined): string | null {
  const key = getPreferredShiftKey(value);
  if (key === "overnight") return "Madrugada";
  if (key === "morning") return "Manha";
  if (key === "afternoon") return "Tarde";
  if (key === "evening") return "Noite";
  return null;
}

export function getPreferredShiftScope(
  primary: string | null | undefined,
  scope: (string | null | undefined)[] | null | undefined,
): PreferredShiftKey[] {
  const resolved: PreferredShiftKey[] = [];
  const append = (value: string | null | undefined) => {
    const key = getPreferredShiftKey(value);
    if (key && !resolved.includes(key)) {
      resolved.push(key);
    }
  };

  append(primary);
  for (const value of scope ?? []) {
    append(value);
  }

  return resolved;
}

export function formatPreferredShiftScope(
  primary: string | null | undefined,
  scope: (string | null | undefined)[] | null | undefined,
): string | null {
  const labels = getPreferredShiftScope(primary, scope)
    .map((shift) => getPreferredShiftLabel(shift))
    .filter(Boolean);
  return labels.length ? labels.join(" + ") : null;
}

export function matchesPreferredShift(value: string | null | undefined, filter: PreferredShiftKey | "all"): boolean {
  if (filter === "all") return true;
  return getPreferredShiftKey(value) === filter;
}

export function matchesPreferredShiftScope(
  value: string | null | undefined,
  primary: string | null | undefined,
  scope: (string | null | undefined)[] | null | undefined,
): boolean {
  const resolvedScope = getPreferredShiftScope(primary, scope);
  if (!resolvedScope.length) return true;
  const key = getPreferredShiftKey(value);
  if (!key) return true;
  return resolvedScope.includes(key);
}
