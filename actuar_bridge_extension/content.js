const SELECTORS = {
  memberSearchInput: ['input[name="search"]', 'input[name="member_search"]', 'input[placeholder*="Aluno"]', 'input[placeholder*="Buscar"]'],
  memberSearchSubmit: ['button[type="submit"]', 'button'],
  memberResultRows: ['[data-testid="member-result"]', "table tbody tr", ".member-row"],
  bodyCompositionTab: ['a', 'button'],
  bodyCompositionForm: ["form", '[data-testid="body-composition-form"]'],
  saveButton: ['button[type="submit"]', 'button', 'input[type="submit"]'],
};

const FIELD_SELECTORS = {
  evaluation_date: ['input[name="evaluation_date"]', 'input[name="date"]', 'input[type="date"]'],
  weight: ['input[name="weight"]', 'input[name="weight_kg"]'],
  body_fat_percent: ['input[name="body_fat_percent"]', 'input[name="fat_pct"]', 'input[name="bodyFat"]'],
  lean_mass_kg: ['input[name="lean_mass_kg"]', 'input[name="fat_free_mass_kg"]'],
  muscle_mass_kg: ['input[name="muscle_mass_kg"]', 'input[name="skeletal_muscle_kg"]'],
  bmi: ['input[name="bmi"]'],
  body_water_percent: ['input[name="body_water_percent"]', 'input[name="water_pct"]'],
  notes: ['textarea[name="notes"]', "textarea"],
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
        manual_fallback: true,
        retryable: false,
        action_log_json: error?.actionLog || [],
      }),
    );
  return true;
});

async function executeJob(job) {
  const searchValue = job.actuar_external_id || normalizeDocument(job.member_document) || job.member_name;
  if (!searchValue) {
    throw buildError("member_context_missing", "Sem contexto suficiente para localizar o aluno no Actuar.");
  }

  const searchInput = await waitForAny(SELECTORS.memberSearchInput, 3000);
  if (!searchInput) {
    throw buildError("actuar_form_changed", "Campo de busca do aluno nao foi encontrado na aba do Actuar.");
  }
  fillInput(searchInput, String(searchValue));

  const searchButton = await waitForButtonByText(["buscar", "pesquisar"], 1000);
  if (searchButton) {
    searchButton.click();
  } else {
    searchInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    searchInput.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", bubbles: true }));
  }

  await sleep(800);
  const rows = findAnyAll(SELECTORS.memberResultRows);
  if (!rows.length) {
    throw buildError("member_not_found", "Aluno nao encontrado na aba do Actuar.");
  }

  const firstRow = rows[0];
  const opener = firstRow.querySelector("a,button") || firstRow;
  opener.click();
  await sleep(1200);

  const bodyTab = await waitForClickableByText(["bioimped", "compos"], 4000);
  if (!bodyTab) {
    throw buildError("actuar_form_changed", "A guia de bioimpedancia/composicao nao foi encontrada.");
  }
  bodyTab.click();
  await sleep(1200);

  const form = await waitForAny(SELECTORS.bodyCompositionForm, 4000);
  if (!form) {
    throw buildError("actuar_form_changed", "O formulario de bioimpedancia nao foi encontrado.");
  }

  const actionLog = [];
  const mappedFields = job?.mapped_fields_json?.mapped_fields || [];
  for (const item of mappedFields) {
    if (!item?.actuar_field || item?.value == null) continue;
    const selectors = FIELD_SELECTORS[item.actuar_field];
    if (!selectors) continue;
    const field = findAny(selectors, form) || findAny(selectors);
    if (!field) {
      if (item.required) {
        throw buildError("actuar_form_changed", `Campo obrigatorio ${item.actuar_field} nao foi encontrado.`, actionLog);
      }
      continue;
    }
    fillInput(field, String(item.value));
    actionLog.push({ event: "filled", field: item.field, actuar_field: item.actuar_field });
  }

  const saveButton = await waitForButtonByText(["salvar"], 4000);
  if (!saveButton) {
    throw buildError("actuar_form_changed", "Botao Salvar nao foi encontrado.", actionLog);
  }
  saveButton.click();
  await sleep(1500);

  return {
    external_id: job.actuar_external_id || searchValue,
    action_log_json: actionLog,
    note: "Executado pela extensao do Actuar Bridge.",
  };
}

function buildError(code, message, actionLog = []) {
  return { code, message, actionLog };
}

function normalizeDocument(value) {
  return String(value || "").replace(/\D+/g, "") || null;
}

function fillInput(element, value) {
  element.focus();
  if ("value" in element) {
    element.value = value;
  }
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function findAny(selectors, root = document) {
  for (const selector of selectors) {
    const match = root.querySelector(selector);
    if (match) return match;
  }
  return null;
}

function findAnyAll(selectors, root = document) {
  for (const selector of selectors) {
    const matches = Array.from(root.querySelectorAll(selector));
    if (matches.length) return matches;
  }
  return [];
}

async function waitForAny(selectors, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const found = findAny(selectors);
    if (found) return found;
    await sleep(200);
  }
  return null;
}

async function waitForButtonByText(texts, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const buttons = Array.from(document.querySelectorAll("button, a, input[type='submit']"));
    const match = buttons.find((element) => {
      const text = `${element.textContent || ""} ${element.value || ""}`.toLowerCase();
      return texts.some((item) => text.includes(item));
    });
    if (match) return match;
    await sleep(200);
  }
  return null;
}

async function waitForClickableByText(texts, timeoutMs) {
  return waitForButtonByText(texts, timeoutMs);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
