function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

const VALID_BRAZILIAN_DDDS = new Set([
  "11", "12", "13", "14", "15", "16", "17", "18", "19",
  "21", "22", "24", "27", "28",
  "31", "32", "33", "34", "35", "37", "38",
  "41", "42", "43", "44", "45", "46", "47", "48", "49",
  "51", "53", "54", "55",
  "61", "62", "63", "64", "65", "66", "67", "68", "69",
  "71", "73", "74", "75", "77", "79",
  "81", "82", "83", "84", "85", "86", "87", "88", "89",
  "91", "92", "93", "94", "95", "96", "97", "98", "99",
]);

function firstName(value: string | null | undefined): string {
  const normalized = value?.trim();
  if (!normalized) return "aluno";
  return normalized.split(/\s+/)[0] ?? "aluno";
}

export function normalizeWhatsAppPhone(phone: string | null | undefined): string | null {
  if (!phone) return null;
  let digits = digitsOnly(phone);
  if (!digits) return null;
  if (digits.startsWith("00")) {
    digits = digits.slice(2);
  }
  const local = digits.startsWith("55") ? digits.slice(2) : digits;
  if (local.length !== 10 && local.length !== 11) return null;
  if (!VALID_BRAZILIAN_DDDS.has(local.slice(0, 2))) return null;
  const subscriber = local.slice(2);
  if (subscriber.length === 9 && !subscriber.startsWith("9")) return null;
  return `55${local}`;
}

export function formatPhoneDisplay(phone: string | null | undefined): string | null {
  const normalized = normalizeWhatsAppPhone(phone);
  if (!normalized) return null;

  const local = normalized.startsWith("55") ? normalized.slice(2) : normalized;
  if (local.length === 11) {
    return `+55 (${local.slice(0, 2)}) ${local.slice(2, 7)}-${local.slice(7)}`;
  }
  if (local.length === 10) {
    return `+55 (${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`;
  }
  return `+${normalized}`;
}

export function buildWhatsAppMessage(
  name: string | null | undefined,
  suggestedMessage?: string | null,
): string {
  if (suggestedMessage?.trim()) return suggestedMessage.trim();
  return `Oi ${firstName(name)}, tudo bem? Quero te ajudar com seu acompanhamento na academia.`;
}

export function buildWhatsAppHref(
  phone: string | null | undefined,
  suggestedMessage?: string | null,
  name?: string | null,
): string | null {
  const normalized = normalizeWhatsAppPhone(phone);
  if (!normalized) return null;

  const message = buildWhatsAppMessage(name, suggestedMessage);
  return `https://wa.me/${normalized}?text=${encodeURIComponent(message)}`;
}
