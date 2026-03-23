function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

function firstName(value: string | null | undefined): string {
  const normalized = value?.trim();
  if (!normalized) return "aluno";
  return normalized.split(/\s+/)[0] ?? "aluno";
}

export function normalizeWhatsAppPhone(phone: string | null | undefined): string | null {
  if (!phone) return null;
  let digits = digitsOnly(phone);
  if (!digits) return null;
  if (!digits.startsWith("55") && digits.length <= 11) {
    digits = `55${digits}`;
  }
  return digits || null;
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
