(() => {
const CONTENT_VERSION = "2026-03-31-fill-visible-body-composition-v6";

if (globalThis.__AI_GYM_OS_ACTUAR_BRIDGE_CONTENT_VERSION__ === CONTENT_VERSION) {
  return;
}
globalThis.__AI_GYM_OS_ACTUAR_BRIDGE_CONTENT_VERSION__ = CONTENT_VERSION;

const ACTUAR_ROUTES = {
  assessmentsSearch: "#/avaliacoes/todas-avaliacoes",
  newEvaluation: (personId) => `#/avaliacoes/avaliacao/${personId}`,
  bodyComposition: (personId) => `#/avaliacoes/avaliacao/${personId}/perimetria`,
};
const ACTUAR_AUTH_STORAGE_KEYS = ["actuarWeb/authorizationData", "authorizationData"];

const SELECTORS = {
  memberSearchInput: 'input[name="search"]',
  memberCard: 'div[id^="card-"]',
  memberProfileLink: 'a[href*="#/avaliacoes/perfil-avaliado/"]',
  protocolSelect: [
    'select[name="protocoloComposicaoCorporalId"]',
    'select[name="ProtocoloComposicaoCorporalId"]',
    'select[name="BodyCompositionProtocolId"]',
    'select[id*="protocoloComposicaoCorporalId" i]',
    'select[id*="BodyCompositionProtocolId" i]',
  ].join(", "),
  weightInput: [
    'input#massa',
    'input[name="massa"]',
    'input[name="Massa"]',
    'input[name="MassaTotalAtual"]',
    'input[name="WeightKg"]',
    'input[id*="massa" i]',
    'input[id*="MassaTotalAtual" i]',
    'input[id*="WeightKg" i]',
  ].join(", "),
  heightInput: [
    'input#estatura',
    'input[name="estatura"]',
    'input[name="Estatura"]',
    'input[name="HeightCm"]',
    'input[id*="estatura" i]',
    'input[id*="HeightCm" i]',
  ].join(", "),
  bodyFatPercentInput: [
    'input[name="PercentualGorduraAtual"]',
    'input[name="CurrentFatPercentage"]',
    'input[id*="PercentualGorduraAtual" i]',
    'input[id*="CurrentFatPercentage" i]',
  ].join(", "),
  muscleMassInput: [
    'input[name="MassaMuscularAtual"]',
    'input[name="CurrentMuscleMass"]',
    'input[id*="MassaMuscularAtual" i]',
    'input[id*="CurrentMuscleMass" i]',
  ].join(", "),
  notesInput: 'textarea[name="notes"], textarea',
  saveButton: 'button.btn.btn-success, button',
};

const FIELD_DEFINITIONS = {
  weight: {
    selectors: [
      'input[name="massa"]',
      'input[name="Massa"]',
      "input#massa",
      'input[name="WeightKg"]',
      'input[id*="WeightKg" i]',
      'input[name="MassaTotalAtual"]',
      'input[id*="MassaTotalAtual" i]',
    ],
    labelHints: ["massa total", "massa", "peso"],
    excludeLabelHints: ["massa muscular", "massa de gordura", "massa magra"],
    fillMode: "all",
    valueType: "decimal",
  },
  height_cm: {
    selectors: [
      'input[name="estatura"]',
      'input[name="Estatura"]',
      "input#estatura",
      'input[name="HeightCm"]',
      'input[id*="HeightCm" i]',
    ],
    labelHints: ["estatura", "altura"],
    fillMode: "first",
    valueType: "integer",
  },
  body_fat_percent: {
    selectors: [
      'input[name="PercentualGorduraAtual"]',
      'input[name="CurrentFatPercentage"]',
      'input[id*="PercentualGorduraAtual" i]',
      'input[id*="CurrentFatPercentage" i]',
    ],
    labelHints: ["percentual gordura", "percentual de gordura", "gordura atual", "gordura"],
    excludeLabelHints: ["massa de gordura"],
    fillMode: "first",
    valueType: "decimal",
  },
  muscle_mass_kg: {
    selectors: [
      'input[name="MassaMuscularAtual"]',
      'input[name="CurrentMuscleMass"]',
      'input[id*="MassaMuscularAtual" i]',
      'input[id*="CurrentMuscleMass" i]',
    ],
    labelHints: ["massa muscular atual", "massa muscular"],
    fillMode: "first",
    valueType: "decimal",
  },
  fat_mass_kg: {
    selectors: [
      'input[name="MassaGorduraAtual"]',
      'input[name="CurrentFatMass"]',
      'input[name="FatMassKg"]',
      'input[id*="MassaGorduraAtual" i]',
      'input[id*="CurrentFatMass" i]',
      'input[id*="FatMassKg" i]',
    ],
    labelHints: ["massa de gordura", "gordura corporal em kg", "gordura em kg"],
    fillMode: "first",
    valueType: "decimal",
  },
  lean_mass_kg: {
    selectors: [
      'input[name="MassaMagraAtual"]',
      'input[name="CurrentLeanMass"]',
      'input[name="LeanMassKg"]',
      'input[name="FatFreeMassKg"]',
      'input[id*="MassaMagraAtual" i]',
      'input[id*="CurrentLeanMass" i]',
      'input[id*="LeanMassKg" i]',
      'input[id*="FatFreeMassKg" i]',
    ],
    labelHints: ["massa magra", "massa livre de gordura"],
    fillMode: "first",
    valueType: "decimal",
  },
  bmi: {
    selectors: [
      'input[name="imc"]',
      'input[name="IMC"]',
      'input[name="Bmi"]',
      'input[name="BMI"]',
      'input[id*="imc" i]',
      'input[id*="bmi" i]',
    ],
    labelHints: ["imc"],
    fillMode: "first",
    valueType: "decimal",
  },
  body_water_percent: {
    selectors: [
      'input[name="PercentualAguaAtual"]',
      'input[name="BodyWaterPercent"]',
      'input[name="CurrentWaterPercentage"]',
      'input[id*="PercentualAguaAtual" i]',
      'input[id*="BodyWaterPercent" i]',
      'input[id*="CurrentWaterPercentage" i]',
    ],
    labelHints: ["percentual de agua", "agua corporal", "agua atual"],
    fillMode: "first",
    valueType: "decimal",
  },
  bmr_kcal: {
    selectors: [
      'input[name="TaxaMetabolicaBasal"]',
      'input[name="BasalMetabolicRate"]',
      'input[name="BmrKcal"]',
      'input[id*="TaxaMetabolicaBasal" i]',
      'input[id*="BasalMetabolicRate" i]',
      'input[id*="BmrKcal" i]',
    ],
    labelHints: ["taxa metabolica basal", "bmr"],
    fillMode: "first",
    valueType: "integer",
  },
  total_energy_kcal: {
    selectors: [
      'input[name="GastoEnergeticoTotal"]',
      'input[name="TotalEnergyKcal"]',
      'input[name="TotalEnergyExpenditure"]',
      'input[id*="GastoEnergeticoTotal" i]',
      'input[id*="TotalEnergyKcal" i]',
      'input[id*="TotalEnergyExpenditure" i]',
    ],
    labelHints: ["gasto energetico total", "energia total", "total energy"],
    fillMode: "first",
    valueType: "integer",
  },
  notes: {
    selectors: [SELECTORS.notesInput],
    labelHints: ["observacoes", "observacoes gerais", "notas", "notes"],
    fillMode: "first",
    valueType: "text",
  },
};

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "ACTUAR_BRIDGE_PING") {
    sendResponse({ ok: true, loaded: true, version: CONTENT_VERSION });
    return false;
  }
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
  const resolvedMember = await resolvePersonId(job, actionLog);
  const personId = resolvedMember.personId;
  await openBodyCompositionForm(personId);
  await ensureManualProtocol();
  actionLog.push(...(await fillMappedFields(job)));
  const assessmentId = await saveAndCaptureAssessment(personId);
  actionLog.push({ event: "actuar_new_assessment_created", person_id: personId, assessment_id: assessmentId });
  return {
    external_id: resolvedMember.persistedExternalId,
    action_log_json: actionLog,
    note: "Executado pela extensao do Actuar Bridge.",
  };
}

async function resolvePersonId(job, actionLog) {
  const linkedExternalId = stripText(job.actuar_external_id);
  if (looksLikeActuarPersonId(linkedExternalId)) {
    actionLog.push({ event: "actuar_member_resolved", strategy: "linked_person_id", person_id: linkedExternalId });
    return {
      personId: linkedExternalId,
      persistedExternalId: linkedExternalId,
    };
  }

  const authContext = resolveActuarAuthContext();
  actionLog.push({
    event: "actuar_lookup_auth_context",
    has_bearer_token: Boolean(authContext?.bearerToken),
  });

  const apiCandidates = await fetchMemberCandidatesViaExtension(job, actionLog, authContext);
  const apiCandidate = selectMemberCandidate(apiCandidates, job);
  if (apiCandidate) {
    actionLog.push({
      event: "actuar_member_resolved",
      strategy: "api_lookup",
      person_id: apiCandidate.personId,
      external_id: apiCandidate.externalId,
      email: apiCandidate.email,
      age: apiCandidate.age,
    });
    return {
      personId: apiCandidate.personId,
      persistedExternalId: linkedExternalId || apiCandidate.externalId || apiCandidate.personId,
    };
  }

  const searchTerms = buildLookupTerms(job);
  if (!searchTerms.length) {
    throw buildError("member_context_missing", "Sem contexto suficiente para localizar o aluno no Actuar.", actionLog);
  }

  await navigateTo(ACTUAR_ROUTES.assessmentsSearch);
  const searchInput = await waitForSelector(SELECTORS.memberSearchInput, 5000);
  if (!searchInput) {
    throw buildError("actuar_form_changed", "Campo de busca do avaliado nao foi encontrado.", actionLog);
  }

  let lastCandidates = [];
  for (const lookup of searchTerms) {
    fillInput(searchInput, lookup.value);
    await sleep(1400);
    const candidates = collectMemberCandidates();
    lastCandidates = candidates;
    const candidate = selectMemberCandidate(candidates, job);
    if (!candidate) {
      continue;
    }

    actionLog.push({
      event: "actuar_member_resolved",
      strategy: lookup.kind,
      search_term: lookup.value,
      person_id: candidate.personId,
      email: candidate.email,
      age: candidate.age,
    });
    return {
      personId: candidate.personId,
      persistedExternalId: linkedExternalId || candidate.externalId || candidate.personId,
    };
  }

  throw buildError(
    lastCandidates.length > 1 ? "member_match_ambiguous" : "member_not_found",
    "Nao foi possivel identificar o aluno correto no Actuar pelos dados disponiveis.",
    [...actionLog, { event: "candidate_count", count: lastCandidates.length }],
  );
}

async function openBodyCompositionForm(personId) {
  await navigateTo(ACTUAR_ROUTES.bodyComposition(personId));
  let formReady = await waitUntilValue(() => findFieldElement("weight") || findProtocolSelect() || findSaveButton(), 8000);
  if (!formReady) {
    await navigateTo(ACTUAR_ROUTES.newEvaluation(personId));
    const bodyCompositionTab = findBodyCompositionTabTrigger();
    if (bodyCompositionTab) {
      bodyCompositionTab.click();
      await sleep(1200);
      formReady = await waitUntilValue(() => findFieldElement("weight") || findProtocolSelect() || findSaveButton(), 10000);
    }
  }
  if (!formReady) {
    const createButton = findCreateEvaluationButton();
    if (createButton) {
      createButton.click();
      await sleep(1200);
      formReady = await waitUntilValue(() => findFieldElement("weight") || findProtocolSelect() || findSaveButton(), 10000);
    }
  }
  if (!formReady) {
    throw buildError("actuar_form_changed", "Formulario real de composicao corporal nao foi encontrado.");
  }
}

async function ensureManualProtocol() {
  const select = findProtocolSelect();
  if (!(select instanceof HTMLSelectElement)) return;
  const option = Array.from(select.options).find(
    (item) => item.value === "0: 0" || (item.textContent || "").includes("Adicionar manualmente"),
  );
  if (!option) return;
  select.value = option.value;
  select.dispatchEvent(new Event("input", { bubbles: true }));
  select.dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(200);
  await waitUntilValue(() => findFieldElement("weight") || findFieldElement("body_fat_percent"), 5000);
}

async function fillMappedFields(job) {
  const actionLog = [];
  const mappedFields = job?.mapped_fields_json?.mapped_fields || [];
  for (const item of mappedFields) {
    const actuarField = item?.actuar_field;
    if (!actuarField) continue;
    const fields = findFieldElements(actuarField);
    if (!fields.length) {
      if (item.required) {
        throw buildError("actuar_form_changed", `Campo obrigatorio ${actuarField} nao foi encontrado.`, actionLog);
      }
      continue;
    }
    const formattedValue = formatFieldValue(actuarField, item.value, fields[0]);
    if (formattedValue == null) {
      if (item.required) {
        throw buildError("critical_fields_missing", `Campo obrigatorio ${actuarField} sem valor valido.`, actionLog);
      }
      continue;
    }
    let appliedCount = 0;
    for (const field of fields) {
      fillInput(field, formattedValue);
      const applied = await waitUntil(() => fieldHasExpectedValue(field, actuarField, formattedValue), 1500);
      if (applied) {
        appliedCount += 1;
      }
    }
    if (appliedCount === 0) {
      if (item.required) {
        throw buildError(
          "actuar_field_not_applied",
          `Campo obrigatorio ${actuarField} nao confirmou o valor informado antes de salvar.`,
          actionLog,
        );
      }
      actionLog.push({ event: "skipped", field: item.field, actuar_field: actuarField, reason: "value_not_applied" });
      continue;
    }
    actionLog.push({
      event: "filled",
      field: item.field,
      actuar_field: actuarField,
      value: formattedValue,
      applied_targets: appliedCount,
      candidate_targets: fields.length,
    });
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
      const text = normalizeComparableText(card.innerText || "");
      if (!text) return null;
      const link = card.querySelector(SELECTORS.memberProfileLink);
      const personId = extractPersonId(link?.getAttribute("href"));
      if (!personId) return null;
      return {
        personId,
        externalId: null,
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

  const expectedExternalId = normalizeText(job.actuar_external_id);
  if (expectedExternalId && !looksLikeActuarPersonId(expectedExternalId)) {
    const externalIdMatches = candidates.filter((candidate) => candidate.text.includes(expectedExternalId));
    if (externalIdMatches.length === 1) return externalIdMatches[0];
  }

  const expectedDocument = resolveLookupDocument(job);
  if (expectedDocument) {
    const documentMatches = candidates.filter((candidate) => {
      const candidateDigits = extractDigits(candidate.text);
      return candidateDigits ? candidateDigits.includes(expectedDocument) : false;
    });
    if (documentMatches.length === 1) return documentMatches[0];
  }

  const expectedEmail = normalizeText(job.member_email);
  if (expectedEmail) {
    const emailMatches = candidates.filter((candidate) => candidate.email === expectedEmail);
    if (emailMatches.length === 1) return emailMatches[0];
  }

  const expectedName = normalizeComparableText(resolveLookupName(job));
  const expectedAgeValue = expectedAge(resolveLookupBirthdate(job));
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

function findProtocolSelect() {
  const direct = document.querySelector(SELECTORS.protocolSelect);
  if (direct instanceof HTMLSelectElement) return direct;
  const fallbackMatches = findElementsByLabel(["protocolo", "manualmente"], ["select"]);
  return fallbackMatches[0] || null;
}

function findBodyCompositionTabTrigger() {
  const triggers = Array.from(document.querySelectorAll("button, a"));
  return (
    triggers.find((element) => {
      const text = normalizeComparableText(element.textContent || "");
      return text && text.includes("composicao corporal e perimetria");
    }) || null
  );
}

function findCreateEvaluationButton() {
  const triggers = Array.from(document.querySelectorAll("button, a"));
  return (
    triggers.find((element) => {
      const text = normalizeComparableText(element.textContent || "");
      return text && (text.includes("nova avalia") || text.includes("novo exame") || text.includes("adicionar avalia"));
    }) || null
  );
}

function findFieldElement(actuarField) {
  return findFieldElements(actuarField)[0] || null;
}

function findFieldElements(actuarField) {
  const definition = FIELD_DEFINITIONS[actuarField];
  if (!definition) return [];

  const allowedTags = actuarField === "notes" ? ["textarea", "input"] : ["input", "textarea"];
  const matches = [];

  for (const selector of definition.selectors || []) {
    Array.from(document.querySelectorAll(selector)).forEach((element) => pushUniqueFieldMatch(matches, element, allowedTags));
  }

  if (!matches.length) {
    const fallbackMatches = findElementsByLabel(definition.labelHints || [], allowedTags, definition.excludeLabelHints || []);
    fallbackMatches.forEach((element) => pushUniqueFieldMatch(matches, element, allowedTags));
  }

  if (definition.fillMode === "all") {
    return matches;
  }
  return matches.length ? [matches[0]] : [];
}

function findElementsByLabel(hints, allowedTags, excludeHints = []) {
  const normalizedHints = hints.map((item) => normalizeComparableText(item)).filter(Boolean);
  const normalizedExcludeHints = excludeHints.map((item) => normalizeComparableText(item)).filter(Boolean);
  if (!normalizedHints.length) return [];

  const candidates = Array.from(document.querySelectorAll("label, span, div, p, strong, small, h1, h2, h3, h4"));
  const matches = [];
  for (const candidate of candidates) {
    const text = normalizeComparableText(candidate.textContent || "");
    if (!text || !normalizedHints.some((hint) => text.includes(hint))) continue;
    if (normalizedExcludeHints.some((hint) => text.includes(hint))) continue;

    const targetFromFor = resolveLabelTarget(candidate, allowedTags);
    if (targetFromFor) pushUniqueFieldMatch(matches, targetFromFor, allowedTags);

    const targetsFromContainer = findElementsNearCandidate(candidate, allowedTags);
    targetsFromContainer.forEach((element) => pushUniqueFieldMatch(matches, element, allowedTags));
  }
  return matches;
}

function resolveLabelTarget(candidate, allowedTags) {
  const forId = candidate.getAttribute("for");
  if (!forId) return null;
  const target = document.getElementById(forId);
  return isEditableAllowedTag(target, allowedTags) ? target : null;
}

function findElementsNearCandidate(candidate, allowedTags) {
  const matches = [];
  let container = candidate;
  for (let depth = 0; container && depth < 4; depth += 1, container = container.parentElement) {
    Array.from(container.querySelectorAll(allowedTags.join(", ")))
      .filter((element) => isEditableAllowedTag(element, allowedTags))
      .forEach((element) => pushUniqueFieldMatch(matches, element, allowedTags));
    if (matches.length) return matches;
  }

  const sibling = candidate.nextElementSibling;
  if (!sibling) return matches;
  if (isEditableAllowedTag(sibling, allowedTags)) {
    pushUniqueFieldMatch(matches, sibling, allowedTags);
  }
  Array.from(sibling.querySelectorAll(allowedTags.join(", ")))
    .filter((element) => isEditableAllowedTag(element, allowedTags))
    .forEach((element) => pushUniqueFieldMatch(matches, element, allowedTags));
  return matches;
}

function fillInput(element, value) {
  element.focus();
  setFieldValue(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
  element.dispatchEvent(new Event("blur", { bubbles: true }));
  if (typeof element.blur === "function") {
    element.blur();
  }
}

function buildLookupTerms(job) {
  return uniqueNonEmpty([
    buildLookupTerm("linked_external_id", stripText(job.actuar_external_id)),
    buildLookupTerm("actuar_search_document", resolveLookupDocument(job)),
    buildLookupTerm("member_document", extractDigits(job.member_document)),
    buildLookupTerm("member_email", stripText(job.member_email)),
    buildLookupTerm("actuar_search_name", stripText(job.actuar_search_name)),
    buildLookupTerm("member_name", stripText(job.member_name)),
  ]);
}

function buildLookupTerm(kind, value) {
  const normalizedValue = stripText(value);
  return normalizedValue ? { kind, value: normalizedValue } : null;
}

async function fetchMemberCandidatesViaExtension(job, actionLog, authContext) {
  const response = await chrome.runtime.sendMessage({ type: "ACTUAR_BRIDGE_FETCH_MEMBER_CANDIDATES", job, authContext }).catch(() => null);
  if (!response?.ok || !Array.isArray(response.candidates)) {
    actionLog.push({
      event: "actuar_lookup_candidates_failed",
      source: "extension_service_worker",
      error: stripText(response?.error) || "unknown_error",
    });
    return [];
  }

  actionLog.push({
    event: "actuar_lookup_candidates",
    source: "extension_service_worker",
    count: response.candidates.length,
  });
  return response.candidates;
}

function resolveLookupName(job) {
  return stripText(job.actuar_search_name) || stripText(job.member_name);
}

function resolveLookupDocument(job) {
  return extractDigits(job.actuar_search_document) || extractDigits(job.member_document);
}

function resolveLookupBirthdate(job) {
  return stripText(job.actuar_search_birthdate) || stripText(job.member_birthdate);
}

function resolveActuarAuthContext() {
  const bearerToken =
    resolveStorageBearerToken(globalThis.localStorage) ||
    resolveStorageBearerToken(globalThis.sessionStorage) ||
    scanStorageForBearerToken(globalThis.localStorage) ||
    scanStorageForBearerToken(globalThis.sessionStorage);
  return bearerToken ? { bearerToken } : null;
}

function resolveStorageBearerToken(storage) {
  if (!storage) return null;
  for (const key of ACTUAR_AUTH_STORAGE_KEYS) {
    try {
      const parsed = JSON.parse(storage.getItem(key) || "null");
      const token = stripText(parsed?.Token || parsed?.token);
      if (token) return token;
    } catch (_error) {}
  }
  return null;
}

function scanStorageForBearerToken(storage) {
  if (!storage) return null;
  const candidates = [];
  try {
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (!key) continue;
      collectJwtCandidates(storage.getItem(key), candidates);
    }
  } catch (_error) {
    return null;
  }
  return pickBearerToken(candidates);
}

function collectJwtCandidates(value, candidates, depth = 0) {
  if (depth > 4 || value == null) return;

  if (typeof value === "string") {
    const tokens = findJwtLikeTokens(value);
    if (tokens.length) {
      candidates.push(...tokens);
      return;
    }
    const normalized = stripText(value);
    if (!normalized || normalized.length > 12000 || (!normalized.startsWith("{") && !normalized.startsWith("["))) {
      return;
    }
    try {
      collectJwtCandidates(JSON.parse(normalized), candidates, depth + 1);
    } catch (_error) {
      return;
    }
    return;
  }

  if (Array.isArray(value)) {
    value.forEach((item) => collectJwtCandidates(item, candidates, depth + 1));
    return;
  }

  if (typeof value === "object") {
    Object.values(value).forEach((item) => collectJwtCandidates(item, candidates, depth + 1));
  }
}

function findJwtLikeTokens(value) {
  const matches = String(value || "").match(/[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g) || [];
  return matches.filter((token) => decodeJwtPayload(token));
}

function pickBearerToken(tokens) {
  const unique = uniqueNonEmpty(tokens);
  const nowSeconds = Math.floor(Date.now() / 1000);
  const unexpired = unique.filter((token) => {
    const payload = decodeJwtPayload(token);
    return !payload?.exp || payload.exp > nowSeconds + 30;
  });
  return stripText(unexpired[0]) || stripText(unique[0]);
}

function decodeJwtPayload(token) {
  const payloadSegment = String(token || "").split(".")[1];
  if (!payloadSegment) return null;
  try {
    const base64 = payloadSegment.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    return JSON.parse(atob(padded));
  } catch (_error) {
    return null;
  }
}

function isAllowedTag(element, allowedTags) {
  if (!isSupportedFieldElement(element)) return false;
  return allowedTags.includes(element.tagName.toLowerCase()) && !isIgnoredInputType(element);
}

function isEditableAllowedTag(element, allowedTags) {
  if (!isAllowedTag(element, allowedTags)) return false;
  if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
    if (element.disabled || element.readOnly) return false;
  }
  if (element instanceof HTMLSelectElement && element.disabled) {
    return false;
  }
  return isVisibleElement(element);
}

function isSupportedFieldElement(element) {
  return element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement || element instanceof HTMLSelectElement;
}

function isIgnoredInputType(element) {
  return element instanceof HTMLInputElement && ["hidden", "button", "submit", "checkbox", "radio", "file"].includes(element.type);
}

function isVisibleElement(element) {
  if (!(element instanceof HTMLElement)) return false;
  const style = window.getComputedStyle(element);
  if (style.display === "none" || style.visibility === "hidden") return false;
  const rects = element.getClientRects();
  return Array.from(rects).some((rect) => rect.width > 0 && rect.height > 0);
}

function pushUniqueFieldMatch(matches, element, allowedTags) {
  if (!isEditableAllowedTag(element, allowedTags)) return;
  if (matches.includes(element)) return;
  matches.push(element);
}

function findSaveButton() {
  const buttons = Array.from(document.querySelectorAll(SELECTORS.saveButton));
  return buttons.find((element) => (element.textContent || "").includes("Salvar")) || null;
}

function formatFieldValue(actuarField, value, element = null) {
  if (value == null || value === "") return null;
  const definition = FIELD_DEFINITIONS[actuarField];
  if (definition?.valueType === "integer") {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return null;
    const rounded = Math.round(numeric);
    return element instanceof HTMLInputElement && element.type === "number" ? String(rounded) : String(rounded);
  }
  if (definition?.valueType === "decimal") {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return null;
    if (element instanceof HTMLInputElement && element.type === "number") {
      return numeric.toFixed(2);
    }
    return numeric.toFixed(2).replace(".", ",");
  }
  return stripText(value);
}

function setFieldValue(element, value) {
  const prototype =
    element instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : element instanceof HTMLInputElement
        ? HTMLInputElement.prototype
        : element instanceof HTMLSelectElement
          ? HTMLSelectElement.prototype
          : null;
  const setter = prototype ? Object.getOwnPropertyDescriptor(prototype, "value")?.set : null;
  if (setter) {
    setter.call(element, value);
    return;
  }
  element.value = value;
}

function fieldHasExpectedValue(element, actuarField, expectedValue) {
  const actualValue = stripText(element.value);
  if (!actualValue) return false;

  if (actuarField === "notes") {
    return normalizeComparableText(actualValue)?.includes(normalizeComparableText(expectedValue));
  }

  if (FIELD_DEFINITIONS[actuarField]?.valueType === "integer") {
    return extractDigits(actualValue) === extractDigits(expectedValue);
  }

  if (FIELD_DEFINITIONS[actuarField]?.valueType === "decimal") {
    const actualNumeric = parseFlexibleNumber(actualValue);
    const expectedNumeric = parseFlexibleNumber(expectedValue);
    if (actualNumeric == null || expectedNumeric == null) return false;
    return Math.abs(actualNumeric - expectedNumeric) < 0.01;
  }

  return normalizeComparableText(actualValue) === normalizeComparableText(expectedValue);
}

function parseFlexibleNumber(value) {
  const normalized = stripText(value);
  if (!normalized) return null;
  const compact = normalized.replace(/\s+/g, "");
  if (/^-?\d+(?:[.,]\d+)?$/.test(compact)) {
    const direct = Number(compact.replace(",", "."));
    return Number.isFinite(direct) ? direct : null;
  }
  const digits = compact.replace(/[^\d,.-]/g, "");
  if (!digits) return null;
  const direct = Number(digits.replace(",", "."));
  return Number.isFinite(direct) ? direct : null;
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
  return normalizeComparableText(String(text || "").split("\n", 1)[0]);
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

function normalizeComparableText(value) {
  const normalized = normalizeText(value);
  return normalized ? normalized.normalize("NFD").replace(/[\u0300-\u036f]/g, "") : null;
}

function looksLikeActuarPersonId(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(value || ""));
}

function extractDigits(value) {
  const digits = String(value || "").replace(/\D+/g, "");
  return digits || null;
}

function stripText(value) {
  const normalized = String(value || "").trim();
  return normalized || null;
}

function uniqueNonEmpty(values) {
  const unique = [];
  const seen = new Set();
  for (const value of values.filter(Boolean)) {
    const key = typeof value === "string" ? value : `${value.kind}:${value.value}`;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(value);
  }
  return unique;
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
})();
