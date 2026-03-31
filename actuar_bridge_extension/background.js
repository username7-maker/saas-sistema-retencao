const RELAY_BASE_URL = "http://127.0.0.1:44777";
const ACTUAR_URL_HINT = "actuar";
const STORAGE_KEY = "actuarBridgeAttachedTab";
const POLL_ALARM = "actuarBridgePoll";

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
  return false;
});

async function attachCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !tab.url || !tab.url.toLowerCase().includes(ACTUAR_URL_HINT)) {
    return { ok: false, error: "Abra a aba do Actuar antes de anexar." };
  }
  await attachTab(tab);
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
  const job = await relayGet("/v1/jobs/next", true);
  if (!job) return;

  try {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
  } catch (_error) {
    // content script may already be present
  }

  const result = await chrome.tabs.sendMessage(tab.id, { type: "ACTUAR_BRIDGE_EXECUTE_JOB", job }).catch((error) => ({
    ok: false,
    error_code: "extension_dispatch_failed",
    error_message: error?.message || "Falha ao enviar o job para a aba do Actuar.",
    manual_fallback: true,
    retryable: false,
  }));

  if (result?.ok) {
    await relayPost(`/v1/jobs/${job.job_id}/complete`, {
      external_id: result.external_id || job.actuar_external_id || null,
      action_log_json: result.action_log_json || [],
      note: result.note || null,
    });
    return;
  }

  await relayPost(`/v1/jobs/${job.job_id}/fail`, {
    error_code: result?.error_code || "extension_execution_failed",
    error_message: result?.error_message || "A extensao nao conseguiu concluir o fluxo do Actuar.",
    retryable: Boolean(result?.retryable),
    manual_fallback: result?.manual_fallback !== false,
    action_log_json: result?.action_log_json || [],
  });
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
