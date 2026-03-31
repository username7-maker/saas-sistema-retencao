const ACTUAR_ROUTES = {
  assessmentsSearch: "#/avaliacoes/todas-avaliacoes",
  bodyComposition: (personId) => `#/avaliacoes/avaliacao/${personId}/perimetria`,
};

const SELECTORS = {
  memberSearchInput: 'input[name="search"]',
  memberCard: 'div[id^="card-"]',
  memberProfileLink: 'a[href*="#/avaliacoes/perfil-avaliado/"]',
  protocolSelect: 'select[name="protocoloComposicaoCorporalId"]',
  weightInput: 'input#massa, input[name="massa"]',
  heightInput: 'input#estatura, input[name="estatura"]',
  bodyFatPercentInput: 'input[name="PercentualGorduraAtual"]',
  muscleMassInput: 'input[name="MassaMuscularAtual"]',
  notesInput: 'textarea[name="notes"], textarea',
  saveButton: 'button.btn.btn-success, button',
};

const FIELD_SELECTORS = {
  weight: SELECTORS.weightInput,
  height_cm: SELECTORS.heightInput,
  body_fat_percent: SELECTORS.bodyFatPercentInput,
  muscle_mass_kg: SELECTORS.muscleMassInput,
  notes: SELECTORS.notesInput,
};

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "ACTUAR_BRIDGE_EXECUTE_JOB") return false;
  executeJob(message.job)
    .then((result) => sendResponse({ ok: true, ...result }))
    .catch((error) =>
      sendResponse({
        ok: false,
        error_code: error?.code || "actuar_form_changed",
        error_message: error?.message || "Falha ao automatizar a aba do Actuar.",
        manual_fallback: error?.manualFallback !== false,
        retryable: Boolean(error?.retryable),
        action_log_json: error?.actionLog || [],
      }),
    );
  return true;
});

async function executeJob(job) {
  const actionLog = [];
  const personId = await resolvePersonId(job, actionLog);
  await openBodyCompositionForm(personId);
  await ensureManualProtocol();
  actionLog.push(...(await fillMappedFields(job)));
  const assessmentId = await saveAndCaptureAssessment(personId);
  actionLog.push({ event: "actuar_new_assessment_created", person_id: personId, assessment_id: assessmentId });
  return {
    external_id: personId,
    action_log_json: actionLog,
    note: "Executado pela extensao do Actuar Bridge.",
  };
}

async function resolvePersonId(job, actionLog) {
  const linkedExternalId = stripText(job.actuar_external_id);
  if (linkedExternalId) {
    actionLog.push({ event: "actuar_member_resolved", strategy: "linked_external_id", person_id: linkedExternalId });
    return linkedExternalId;
  }

  const memberName = stripText(job.member_name);
  if (!memberName) {
    throw buildError("member_context_missing", "Sem contexto suficiente para localizar o aluno no Actuar.", actionLog);
  }

  await navigateTo(ACTUAR_ROUTES.assessmentsSearch);
  const searchInput = await waitForSelector(SELECTORS.memberSearchInput, 5000);
  if (!searchInput) {
    throw buildError("actuar_form_changed", "Campo de busca do avaliado nao foi encontrado.", actionLog);
  }

  fillInput(searchInput, memberName);
  await sleep(1400);
  const candidates = collectMemberCandidates();
  const candidate = selectMemberCandidate(candidates, job);
  if (!candidate) {
    throw buildError(
      candidates.length > 1 ? "member_match_ambiguous" : "member_not_found",
      "Nao foi possivel identificar o aluno correto no Actuar pela lista de avaliados.",
      [...actionLog, { event: "candidate_count", count: candidates.length }],
    );
  }

  actionLog.push({
    event: "actuar_member_resolved",
    strategy: "search_results",
    person_id: candidate.personId,
    email: candidate.email,
    age: candidate.age,
  });
  return candidate.personId;
}

async function openBodyCompositionForm(personId) {
  await navigateTo(ACTUAR_ROUTES.bodyComposition(personId));
  const formReady = await waitUntilValue(
    () =>
      document.querySelector(SELECTORS.weightInput) ||
      document.querySelector(SELECTORS.protocolSelect) ||
      findSaveButton(),
    15000,
  );
  if (!formReady) {
    throw buildError("actuar_form_changed", "Formulario real de composicao corporal nao foi encontrado.");
  }
}

async function ensureManualProtocol() {
  const select = document.querySelector(SELECTORS.protocolSelect);
  if (!(select instanceof HTMLSelectElement)) return;
  const option = Array.from(select.options).find(
    (item) => item.value === "0: 0" || (item.textContent || "").includes("Adicionar manualmente"),
  );
  if (!option) return;
  select.value = option.value;
  select.dispatchEvent(new Event("input", { bubbles: true }));
  select.dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(200);
}

async function fillMappedFields(job) {
  const actionLog = [];
  const mappedFields = job?.mapped_fields_json?.mapped_fields || [];
  for (const item of mappedFields) {
    const actuarField = item?.actuar_field;
    if (!actuarField) continue;
    const selector = FIELD_SELECTORS[actuarField];
    if (!selector) continue;
    const field = document.querySelector(selector);
    if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement)) {
      if (item.required) {
        throw buildError("actuar_form_changed", `Campo obrigatorio ${actuarField} nao foi encontrado.`, actionLog);
      }
      continue;
    }
    const formattedValue = formatFieldValue(actuarField, item.value);
    if (formattedValue == null) {
      if (item.required) {
        throw buildError("critical_fields_missing", `Campo obrigatorio ${actuarField} sem valor valido.`, actionLog);
      }
      continue;
    }
    fillInput(field, formattedValue);
    actionLog.push({ event: "filled", field: item.field, actuar_field: actuarField, value: formattedValue });
    if (item.field === "height_cm" && item.classification === "critical_derived") {
      actionLog.push({ event: "height_derived_from_weight_and_bmi", value: formattedValue });
    }
  }
  await sleep(300);
  return actionLog;
}

async function saveAndCaptureAssessment(personId) {
  const saveButton = await waitForSaveButton(4000);
  if (!saveButton) {
    throw buildError("actuar_form_changed", "Botao Salvar nao foi encontrado.");
  }

  saveButton.click();
  const ok = await waitUntil(
    () => {
      const hash = window.location.hash || "";
      const prefix = `#/avaliacoes/avaliacao/${personId}/`;
      return hash.startsWith(prefix) && !hash.endsWith("/perimetria");
    },
    10000,
  );
  if (!ok) {
    throw buildError("actuar_save_not_confirmed", "O Actuar nao confirmou a criacao da nova avaliacao no tempo esperado.");
  }
  return extractAssessmentId(window.location.href, personId);
}

function collectMemberCandidates() {
  return Array.from(document.querySelectorAll(SELECTORS.memberCard))
    .map((card) => {
      const text = normalizeText(card.innerText || "");
      if (!text) return null;
      const link = card.querySelector(SELECTORS.memberProfileLink);
      const personId = extractPersonId(link?.getAttribute("href"));
      if (!personId) return null;
      return {
        personId,
        name: extractName(text),
        email: extractEmail(text),
        age: extractAge(text),
        text,
      };
    })
    .filter(Boolean);
}

function selectMemberCandidate(candidates, job) {
  if (!candidates.length) return null;
  if (candidates.length === 1) return candidates[0];

  const expectedEmail = normalizeText(job.member_email);
  if (expectedEmail) {
    const emailMatches = candidates.filter((candidate) => candidate.email === expectedEmail);
    if (emailMatches.length === 1) return emailMatches[0];
  }

  const expectedName = normalizeText(job.member_name);
  const expectedAgeValue = expectedAge(job.member_birthdate);
  const exactNameMatches = candidates.filter((candidate) => candidate.name === expectedName);
  if (expectedAgeValue != null) {
    const ageMatches = exactNameMatches.filter((candidate) => candidate.age === expectedAgeValue);
    if (ageMatches.length === 1) return ageMatches[0];
  }
  if (exactNameMatches.length === 1) return exactNameMatches[0];
  return null;
}

async function navigateTo(hash) {
  if (window.location.hash !== hash) {
    window.location.hash = hash.replace(/^#/, "#");
  }
  await sleep(1200);
}

async function waitForSelector(selector, timeoutMs) {
  return await waitUntilValue(() => document.querySelector(selector), timeoutMs);
}

async function waitForSaveButton(timeoutMs) {
  return await waitUntilValue(() => findSaveButton(), timeoutMs);
}

async function waitUntil(predicate, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    if (predicate()) return true;
    await sleep(200);
  }
  return false;
}

async function waitUntilValue(factory, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const value = factory();
    if (value) return value;
    await sleep(200);
  }
  return null;
}

function buildError(code, message, actionLog = [], retryable = false, manualFallback = true) {
  return { code, message, actionLog, retryable, manualFallback };
}

function fillInput(element, value) {
  element.focus();
  element.value = value;
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function findSaveButton() {
  const buttons = Array.from(document.querySelectorAll(SELECTORS.saveButton));
  return buttons.find((element) => (element.textContent || "").includes("Salvar")) || null;
}

function formatFieldValue(actuarField, value) {
  if (value == null || value === "") return null;
  if (actuarField === "height_cm") {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? String(Math.round(numeric)) : null;
  }
  if (["weight", "body_fat_percent", "muscle_mass_kg"].includes(actuarField)) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric.toFixed(2).replace(".", ",") : null;
  }
  return stripText(value);
}

function extractPersonId(href) {
  if (!href) return null;
  const match = href.match(/\/avaliacoes\/perfil-avaliado\/([^/?#]+)/);
  return match ? match[1] : null;
}

function extractAssessmentId(url, personId) {
  const match = String(url || "").match(new RegExp(`/avaliacoes/avaliacao/${escapeRegExp(personId)}/([^/?#]+)$`));
  return match ? match[1] : null;
}

function extractName(text) {
  return normalizeText(String(text || "").split("\n", 1)[0]);
}

function extractEmail(text) {
  const match = String(text || "").match(/[\w.+-]+@[\w.-]+\.\w+/i);
  return match ? normalizeText(match[0]) : null;
}

function extractAge(text) {
  const match = String(text || "").match(/(\d{1,3})\s+anos/i);
  return match ? Number(match[1]) : null;
}

function expectedAge(birthdate) {
  const raw = stripText(birthdate);
  if (!raw) return null;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return null;
  const today = new Date();
  let age = today.getFullYear() - parsed.getFullYear();
  const beforeBirthday =
    today.getMonth() < parsed.getMonth() ||
    (today.getMonth() === parsed.getMonth() && today.getDate() < parsed.getDate());
  if (beforeBirthday) age -= 1;
  return age;
}

function normalizeText(value) {
  const stripped = stripText(value);
  return stripped ? stripped.toLowerCase() : null;
}

function stripText(value) {
  const normalized = String(value || "").trim();
  return normalized || null;
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
