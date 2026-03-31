const relayStatus = document.getElementById("relayStatus");
const tabStatus = document.getElementById("tabStatus");
const tabMeta = document.getElementById("tabMeta");
const attachButton = document.getElementById("attachButton");
const detachButton = document.getElementById("detachButton");

attachButton.addEventListener("click", async () => {
  const result = await chrome.runtime.sendMessage({ type: "ACTUAR_BRIDGE_ATTACH_TAB" });
  if (!result?.ok) {
    tabStatus.textContent = result?.error || "Nao foi possivel anexar a aba atual.";
    tabStatus.className = "status warn";
    return;
  }
  await refresh();
});

detachButton.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "ACTUAR_BRIDGE_DETACH_TAB" });
  await refresh();
});

async function refresh() {
  const relay = await fetch("http://127.0.0.1:44777/health").then((response) => response.json()).catch(() => null);
  const state = await chrome.runtime.sendMessage({ type: "ACTUAR_BRIDGE_GET_STATE" });

  if (relay?.ok) {
    relayStatus.textContent = `Relay local: online${relay.pending_job_id ? ` • job ${relay.pending_job_id}` : ""}`;
    relayStatus.className = "status ok";
  } else {
    relayStatus.textContent = "Relay local: offline";
    relayStatus.className = "status warn";
  }

  if (state?.tabId) {
    tabStatus.textContent = "Aba: anexada";
    tabStatus.className = "status ok";
    tabMeta.textContent = state.url || "";
  } else {
    tabStatus.textContent = "Aba: nao anexada";
    tabStatus.className = "status warn";
    tabMeta.textContent = "";
  }
}

void refresh();
