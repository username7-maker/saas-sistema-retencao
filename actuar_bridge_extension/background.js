const RELAY_BASE_URL = "http://127.0.0.1:44777";
const ACTUAR_URL_HINT = "actuar";
const STORAGE_KEY = "actuarBridgeAttachedTab";
const POLL_ALARM = "actuarBridgePoll";
const CONTENT_SCRIPT_VERSION = "2026-03-31-fill-visible-body-composition-v6";
const ACTUAR_API = {
  odata: "https://odata.prd.g.actuar.cloud",
  physicalAssessmentService: "https://physicalassessmentservice-api.prd.g.actuar.cloud",
};
const ACTUAR_AUTH_STORAGE_KEYS = ["actuarWeb/authorizationData", "authorizationData"];

async function ensureAlarm() {
  await chrome.alarms.clear(POLL_ALARM);
  chrome.alarms.create(POLL_ALARM, { periodInMinutes: 0.05 });
}

chrome.runtime.onInstalled.addListener(() => {
  void ensureAlarm();
});

chrome.runtime.onStartup.addListener(() => {
  void ensureAlarm();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name !== POLL_ALARM) return;
  void pollRelayAndExecute();
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "ACTUAR_BRIDGE_ATTACH_TAB") {
    void attachCurrentTab().then(sendResponse);
    return true;
  }
  if (message?.type === "ACTUAR_BRIDGE_DETACH_TAB") {
    void detachTab().then(sendResponse);
    return true;
  }
  if (message?.type === "ACTUAR_BRIDGE_GET_STATE") {
    void getExtensionState().then(sendResponse);
    return true;
  }
  if (message?.type === "ACTUAR_BRIDGE_FETCH_MEMBER_CANDIDATES") {
    void fetchMemberCandidates(message.job, message.authContext).then((candidates) => sendResponse({ ok: true, candidates })).catch((error) =>
      sendResponse({
        ok: false,
        error: error?.message || "Falha ao consultar candidatos do Actuar.",
      }),
    );
    return true;
  }
  return false;
});

async function attachCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !tab.url || !tab.url.toLowerCase().includes(ACTUAR_URL_HINT)) {
    return { ok: false, error: "Abra a aba do Actuar antes de anexar." };
  }
  await attachTab(tab);
  await executePendingJob(tab);
  return { ok: true, tabId: tab.id, url: tab.url };
}

async function attachFirstActuarTab() {
  const tabs = await chrome.tabs.query({});
  const tab = tabs.find((item) => item?.id && item.url && item.url.toLowerCase().includes(ACTUAR_URL_HINT));
  if (!tab?.id || !tab.url) {
    await postBrowserStatus({ attached: false });
    return null;
  }
  await attachTab(tab);
  return tab;
}

async function attachTab(tab) {
  await chrome.storage.local.set({
    [STORAGE_KEY]: {
      tabId: tab.id,
      url: tab.url,
      title: tab.title || "Actuar",
      attachedAt: new Date().toISOString(),
    },
  });
  await postBrowserStatus({ attached: true, tab_id: tab.id, url: tab.url, title: tab.title || "Actuar" });
}

async function detachTab() {
  await chrome.storage.local.remove(STORAGE_KEY);
  await postBrowserStatus({ attached: false });
  return { ok: true };
}

async function getExtensionState() {
  const state = await chrome.storage.local.get(STORAGE_KEY);
  return state[STORAGE_KEY] || null;
}

async function pollRelayAndExecute() {
  const stored = await chrome.storage.local.get(STORAGE_KEY);
  const attached = stored[STORAGE_KEY] || null;
  if (!attached?.tabId) {
    const autoAttachedTab = await attachFirstActuarTab();
    if (!autoAttachedTab?.id) {
      await postBrowserStatus({ attached: false });
      return;
    }
  }

  const latestStored = await chrome.storage.local.get(STORAGE_KEY);
  const resolvedAttached = latestStored[STORAGE_KEY] || null;
  const tab = await chrome.tabs.get(resolvedAttached?.tabId).catch(() => null);
  if (!tab?.id || !tab.url || !tab.url.toLowerCase().includes(ACTUAR_URL_HINT)) {
    await chrome.storage.local.remove(STORAGE_KEY);
    const autoAttachedTab = await attachFirstActuarTab();
    if (!autoAttachedTab?.id) {
      await postBrowserStatus({ attached: false });
      return;
    }
    const refreshedStored = await chrome.storage.local.get(STORAGE_KEY);
    const refreshedAttached = refreshedStored[STORAGE_KEY] || null;
    const refreshedTab = await chrome.tabs.get(refreshedAttached?.tabId).catch(() => null);
    if (!refreshedTab?.id || !refreshedTab.url) {
      await postBrowserStatus({ attached: false });
      return;
    }
    await postBrowserStatus({ attached: true, tab_id: refreshedTab.id, url: refreshedTab.url, title: refreshedTab.title || "Actuar" });
    return await executePendingJob(refreshedTab);
  }

  await postBrowserStatus({ attached: true, tab_id: tab.id, url: tab.url, title: tab.title || "Actuar" });
  return await executePendingJob(tab);
}

async function executePendingJob(tab) {
  try {
    const job = await relayGet("/v1/jobs/next", true);
    if (!job) return;

    await ensureContentScript(tab.id);

    const result = await chrome.tabs.sendMessage(tab.id, { type: "ACTUAR_BRIDGE_EXECUTE_JOB", job }).catch((error) => ({
      ok: false,
      error_code: "extension_dispatch_failed",
      error_message: error?.message || "Falha ao enviar o job para a aba do Actuar.",
      manual_fallback: true,
      retryable: false,
    }));

    if (result?.ok) {
      const completion = await relayPost(`/v1/jobs/${job.job_id}/complete`, {
        external_id: result.external_id || job.actuar_external_id || null,
        action_log_json: result.action_log_json || [],
        note: result.note || null,
      });
      if (completion?.conflict) {
        return;
      }
      return;
    }

    const failure = await relayPost(`/v1/jobs/${job.job_id}/fail`, {
      error_code: result?.error_code || "extension_execution_failed",
      error_message: result?.error_message || "A extensao nao conseguiu concluir o fluxo do Actuar.",
      retryable: Boolean(result?.retryable),
      manual_fallback: result?.manual_fallback !== false,
      action_log_json: result?.action_log_json || [],
    });
    if (failure?.conflict) {
      return;
    }
  } catch (_error) {
    return;
  }
}

async function ensureContentScript(tabId) {
  const ping = await chrome.tabs.sendMessage(tabId, { type: "ACTUAR_BRIDGE_PING" }).catch(() => null);
  if (ping?.ok && ping.version === CONTENT_SCRIPT_VERSION) return;

  if (ping?.ok && ping.version !== CONTENT_SCRIPT_VERSION) {
    await chrome.tabs.reload(tabId);
    await waitForTabLoad(tabId);
  }

  try {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
  } catch (_error) {
    // the script may already be attached but not reachable during navigation
  }

  const loadedPing = await chrome.tabs.sendMessage(tabId, { type: "ACTUAR_BRIDGE_PING" }).catch(() => null);
  if (loadedPing?.ok && loadedPing.version === CONTENT_SCRIPT_VERSION) {
    return;
  }

  throw new Error("Actuar content script not ready.");
}

async function waitForTabLoad(tabId, timeoutMs = 15000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const tab = await chrome.tabs.get(tabId).catch(() => null);
    if (tab?.status === "complete") {
      return;
    }
    await sleep(250);
  }
}

async function relayGet(path, allowNoContent = false) {
  const response = await fetch(`${RELAY_BASE_URL}${path}`);
  if (allowNoContent && response.status === 204) return null;
  if (!response.ok) {
    throw new Error(`Relay GET failed: ${response.status}`);
  }
  return await response.json();
}

async function relayPost(path, payload) {
  const response = await fetch(`${RELAY_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  if (response.status === 409) {
    return { conflict: true };
  }
  if (!response.ok) {
    throw new Error(`Relay POST failed: ${response.status}`);
  }
  return await response.json().catch(() => ({}));
}

async function postBrowserStatus(payload) {
  try {
    return await relayPost("/v1/browser/status", payload);
  } catch (_error) {
    return null;
  }
}

async function fetchMemberCandidates(job, authContext) {
  const headers = buildActuarApiHeaders(authContext);
  const candidates = [];

  const externalCode = resolveLookupExternalCode(job);
  if (externalCode) {
    candidates.push(...(await fetchODataPeopleByCode(externalCode, headers)));
    const deduped = dedupeCandidates(candidates);
    if (deduped.length) {
      return deduped;
    }
  }

  const document = resolveLookupDocument(job);
  if (document) {
    candidates.push(...(await fetchODataPeopleByDocument(document, headers)));
    const deduped = dedupeCandidates(candidates);
    if (deduped.length) {
      return deduped;
    }
  }

  const email = stripText(job?.member_email);
  if (email) {
    candidates.push(...(await fetchODataPeopleByEmail(email, headers)));
    const deduped = dedupeCandidates(candidates);
    if (deduped.length) {
      return deduped;
    }
  }

  const queries = buildJobNameQueries(job);
  for (const query of queries) {
    candidates.push(...(await fetchODataPeopleCandidates(query, headers)));
    candidates.push(...(await fetchPhysicalAssessmentCandidates(query, headers)));
    const deduped = dedupeCandidates(candidates);
    if (deduped.length) {
      return deduped;
    }
  }
  return dedupeCandidates(candidates);
}

async function fetchODataPeopleCandidates(nameQuery, headers) {
  const params = new URLSearchParams({
    $filter: `contains(tolower(NomeCompleto), tolower('${escapeODataString(nameQuery)}')) and ((Modulo eq 'Afig') or (Origem eq 'Afig'))`,
    $skip: "0",
    $top: "25",
    $orderby: "NomeCompleto asc",
    $select: "PessoaId,PessoaCd,NomeCompleto,Idade,Email,Cpf,DataNascimento",
  });
  const response = await fetch(`${ACTUAR_API.odata}/Pessoas?${params.toString()}`, {
    credentials: "include",
    headers,
  });
  if (!response.ok) return [];
  const payload = await response.json();
  return normalizeApiCandidates(payload, {
    personId: "PessoaId",
    externalId: "PessoaCd",
    name: "NomeCompleto",
    email: "Email",
    age: "DataNascimento",
    textKeys: ["PessoaCd", "Cpf", "DataNascimento"],
  });
}

async function fetchPhysicalAssessmentCandidates(nameQuery, headers) {
  const params = new URLSearchParams({
    $filter: `contains(tolower(FullName), tolower('${escapeODataString(nameQuery)}'))`,
    $skip: "0",
    $top: "25",
    $orderby: "FullName asc",
    $select: "PersonId,FullName,Birthdate,Email,AssessmentCount",
  });
  const response = await fetch(`${ACTUAR_API.physicalAssessmentService}/OData/Persons?${params.toString()}`, {
    credentials: "include",
    headers,
  });
  if (!response.ok) return [];
  const payload = await response.json();
  return normalizeApiCandidates(payload, {
    personId: "PersonId",
    name: "FullName",
    email: "Email",
    age: "Birthdate",
    textKeys: ["Birthdate"],
  });
}

function normalizeApiCandidates(payload, fields) {
  const items = Array.isArray(payload?.value) ? payload.value : Array.isArray(payload) ? payload : [];
  return items
    .map((item) => {
      const personId = stripText(item?.[fields.personId]);
      if (!personId) return null;
      const rawName = stripText(item?.[fields.name]);
      return {
        personId,
        externalId: stripText(item?.[fields.externalId]),
        name: normalizeComparableText(rawName),
        email: normalizeText(item?.[fields.email]),
        age: coerceCandidateAge(item?.[fields.age]),
        text: normalizeComparableText(
          [rawName, item?.[fields.email], item?.[fields.age], ...(fields.textKeys || []).map((key) => item?.[key])]
            .filter(Boolean)
            .join(" "),
        ),
      };
    })
    .filter(Boolean);
}

function buildJobNameQueries(job) {
  return uniqueNonEmpty([
    ...buildMemberNameQueries(resolveLookupName(job)),
    ...buildMemberNameQueries(stripText(job?.member_name)),
  ]);
}

function buildMemberNameQueries(name) {
  const rawName = stripText(name);
  if (!rawName) return [];
  const tokens = rawName.split(/\s+/).filter(Boolean);
  return uniqueNonEmpty([
    rawName,
    tokens.length >= 2 ? `${tokens[0]} ${tokens[tokens.length - 1]}` : null,
    tokens.length >= 2 ? `${tokens[0]} ${tokens[1]}` : null,
    tokens[0] || null,
  ]);
}

function resolveLookupName(job) {
  return stripText(job?.actuar_search_name) || stripText(job?.member_name);
}

function resolveLookupDocument(job) {
  return extractDigits(job?.actuar_search_document) || extractDigits(job?.member_document);
}

function resolveLookupExternalCode(job) {
  const externalId = stripText(job?.actuar_external_id);
  if (!externalId || looksLikeUuid(externalId)) return null;
  return /^\d+$/.test(externalId) ? externalId : null;
}

function buildActuarApiHeaders(authContext) {
  const headers = {
    Accept: "application/json",
    "X-Requested-With": "XMLHttpRequest",
  };
  const bearerToken = stripText(authContext?.bearerToken);
  if (bearerToken) {
    headers.Authorization = `Bearer ${bearerToken}`;
  }
  return headers;
}

function dedupeCandidates(candidates) {
  const unique = [];
  const seen = new Set();
  for (const candidate of candidates) {
    const personId = stripText(candidate?.personId);
    if (!personId || seen.has(personId)) continue;
    seen.add(personId);
    unique.push(candidate);
  }
  return unique;
}

function extractDigits(value) {
  const digits = String(value || "").replace(/\D+/g, "");
  return digits || null;
}

function coerceCandidateAge(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.trunc(value);
  }
  const directAge = Number(value);
  if (Number.isFinite(directAge)) {
    return Math.trunc(directAge);
  }
  const parsed = new Date(String(value || ""));
  if (Number.isNaN(parsed.getTime())) return null;
  return expectedAge(parsed.toISOString());
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

function looksLikeUuid(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(value || ""));
}

function stripText(value) {
  const normalized = String(value || "").trim();
  return normalized || null;
}

function uniqueNonEmpty(values) {
  const unique = [];
  const seen = new Set();
  for (const value of values.filter(Boolean)) {
    if (seen.has(value)) continue;
    seen.add(value);
    unique.push(value);
  }
  return unique;
}

function escapeODataString(value) {
  return String(value || "").replace(/'/g, "''");
}

async function fetchODataPeopleByCode(externalCode, headers) {
  const params = new URLSearchParams({
    $filter: `PessoaCd eq ${Number(externalCode)}`,
    $skip: "0",
    $top: "5",
    $orderby: "NomeCompleto asc",
    $select: "PessoaId,PessoaCd,NomeCompleto,Idade,Email,Cpf,DataNascimento",
  });
  const response = await fetch(`${ACTUAR_API.odata}/Pessoas?${params.toString()}`, {
    credentials: "include",
    headers,
  });
  if (!response.ok) return [];
  return normalizeApiCandidates(await response.json(), {
    personId: "PessoaId",
    externalId: "PessoaCd",
    name: "NomeCompleto",
    email: "Email",
    age: "DataNascimento",
    textKeys: ["PessoaCd", "Cpf", "DataNascimento"],
  });
}

async function fetchODataPeopleByDocument(document, headers) {
  const params = new URLSearchParams({
    $filter: `Cpf eq '${escapeODataString(document)}'`,
    $skip: "0",
    $top: "5",
    $orderby: "NomeCompleto asc",
    $select: "PessoaId,PessoaCd,NomeCompleto,Idade,Email,Cpf,DataNascimento",
  });
  const response = await fetch(`${ACTUAR_API.odata}/Pessoas?${params.toString()}`, {
    credentials: "include",
    headers,
  });
  if (!response.ok) return [];
  return normalizeApiCandidates(await response.json(), {
    personId: "PessoaId",
    externalId: "PessoaCd",
    name: "NomeCompleto",
    email: "Email",
    age: "DataNascimento",
    textKeys: ["PessoaCd", "Cpf", "DataNascimento"],
  });
}

async function fetchODataPeopleByEmail(email, headers) {
  const params = new URLSearchParams({
    $filter: `tolower(Email) eq tolower('${escapeODataString(email)}')`,
    $skip: "0",
    $top: "5",
    $orderby: "NomeCompleto asc",
    $select: "PessoaId,PessoaCd,NomeCompleto,Idade,Email,Cpf,DataNascimento",
  });
  const response = await fetch(`${ACTUAR_API.odata}/Pessoas?${params.toString()}`, {
    credentials: "include",
    headers,
  });
  if (!response.ok) return [];
  return normalizeApiCandidates(await response.json(), {
    personId: "PessoaId",
    externalId: "PessoaCd",
    name: "NomeCompleto",
    email: "Email",
    age: "DataNascimento",
    textKeys: ["PessoaCd", "Cpf", "DataNascimento"],
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
