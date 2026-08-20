import { mkdirSync } from "node:fs";

import { expect, test } from "@playwright/test";

const EVIDENCE_DIR = "../.planning/phases/09.18-body-composition-anthropometry-v1/evidence";

function bodyCompositionReport() {
  return {
    header: {
      member_name: "Erick Bedin",
      gym_name: "ProGym Piloto",
      trainer_name: "Automicai Owner",
      measured_at: "2026-04-14T10:00:00Z",
      age_years: 21,
      sex: "male",
      height_cm: 178,
      weight_kg: 84.5,
    },
    current_evaluation_id: "eval-1",
    previous_evaluation_id: "eval-0",
    reviewed_manually: true,
    parsing_confidence: 0.91,
    data_quality_flags: ["body_fat_source_divergence"],
    body_fat_context: {
      bioimpedance_raw_percent: 31.2,
      anthropometric_percent: 23.8,
      used_percent: 23.8,
      used_source: "anthropometry",
      preferred_source: "geneos_composite",
      method: "geneos_composite",
      confidence: "medium_high",
      range_min: 21.8,
      range_max: 25.8,
      difference_between_sources: 7.4,
      manual_review_required: true,
      manual_review_completed: true,
      quality_flags: ["body_fat_source_divergence"],
    },
    measurement_rows: [
      {
        key: "neck_cm",
        label: "Pescoco",
        current_value: 39,
        previous_value: 39.5,
        delta: -0.5,
        unit: "cm",
        used_for_body_fat_calculation: true,
        formatted_current: "39 cm",
        formatted_previous: "39.5 cm",
        formatted_delta: "-0.5 cm",
      },
      {
        key: "abdomen_cm",
        label: "Abdomen",
        current_value: 88,
        previous_value: 92,
        delta: -4,
        unit: "cm",
        used_for_body_fat_calculation: true,
        formatted_current: "88 cm",
        formatted_previous: "92 cm",
        formatted_delta: "-4 cm",
      },
      {
        key: "right_arm_flexed_cm",
        label: "Braco direito contraido",
        current_value: 36,
        previous_value: 35,
        delta: 1,
        unit: "cm",
        used_for_body_fat_calculation: false,
        formatted_current: "36 cm",
        formatted_previous: "35 cm",
        formatted_delta: "+1 cm",
      },
    ],
    primary_cards: [
      { key: "weight_kg", label: "Peso", value: 84.5, unit: "kg", formatted_value: "84.5 kg", delta_absolute: -1.2, delta_percent: -1.4, trend: "down" },
      { key: "body_fat_used_percent", label: "Gordura corporal estimada", value: 23.8, unit: "%", formatted_value: "23.8%", delta_absolute: -1.8, delta_percent: -7.3, trend: "down" },
      { key: "visceral_fat_level", label: "Gordura visceral", value: 9, unit: null, formatted_value: "9", delta_absolute: 0, delta_percent: 0, trend: "stable" },
      { key: "muscle_mass_kg", label: "Massa muscular", value: 35.6, unit: "kg", formatted_value: "35.6 kg", delta_absolute: 0.4, delta_percent: 1.1, trend: "up" },
      { key: "bmi", label: "IMC", value: 26.7, unit: null, formatted_value: "26.7", delta_absolute: -0.3, delta_percent: -1.1, trend: "down" },
      { key: "basal_metabolic_rate_kcal", label: "Metabolismo basal", value: 1880, unit: "kcal", formatted_value: "1880 kcal", delta_absolute: 32, delta_percent: 1.7, trend: "up" },
    ],
    composition_metrics: [
      { key: "body_fat_used_percent", label: "Gordura corporal estimada", value: 23.8, unit: "%", formatted_value: "23.8%", reference_min: 21.8, reference_max: 25.8, status: "adequate", hint: "21.8% a 25.8%" },
      { key: "body_fat_bioimpedance_percent", label: "Gordura corporal bruta da bioimpedancia", value: 31.2, unit: "%", formatted_value: "31.2%", reference_min: 10, reference_max: 25, status: "high", hint: "10% a 25%" },
      { key: "body_fat_anthropometric_percent", label: "Gordura estimada por medidas", value: 23.8, unit: "%", formatted_value: "23.8%", reference_min: 21.8, reference_max: 25.8, status: "adequate", hint: "21.8% a 25.8%" },
      { key: "fat_mass_estimated_kg", label: "Massa de gordura estimada", value: 20.1, unit: "kg", formatted_value: "20.1 kg", reference_min: 5, reference_max: 30, status: "adequate", hint: "5 kg a 30 kg" },
      { key: "lean_mass_estimated_kg", label: "Massa livre de gordura estimada", value: 64.4, unit: "kg", formatted_value: "64.4 kg", reference_min: 35, reference_max: 90, status: "adequate", hint: "35 kg a 90 kg" },
      { key: "body_water_percent", label: "Agua corporal (%)", value: 51.2, unit: "%", formatted_value: "51.2%", reference_min: null, reference_max: null, status: "unknown", hint: null },
      { key: "muscle_mass_kg", label: "Massa muscular", value: 35.6, unit: "kg", formatted_value: "35.6 kg", reference_min: 28, reference_max: 38, status: "adequate", hint: "28 kg a 38 kg" },
    ],
    muscle_fat_metrics: [
      { key: "weight_kg", label: "Peso", value: 84.5, unit: "kg", formatted_value: "84.5 kg", reference_min: 65, reference_max: 80, status: "high", hint: "65 kg a 80 kg" },
      { key: "skeletal_muscle_kg", label: "Musculo esqueletico", value: 35.6, unit: "kg", formatted_value: "35.6 kg", reference_min: 28, reference_max: 38, status: "adequate", hint: "28 kg a 38 kg" },
      { key: "fat_mass_estimated_kg", label: "Massa de gordura estimada", value: 20.1, unit: "kg", formatted_value: "20.1 kg", reference_min: 5, reference_max: 30, status: "adequate", hint: "5 kg a 30 kg" },
    ],
    risk_metrics: [
      { key: "bmi", label: "IMC", value: 26.7, unit: null, formatted_value: "26.7", reference_min: 18.5, reference_max: 24.9, status: "high", hint: "18.5 a 24.9" },
      { key: "body_fat_used_percent", label: "Gordura corporal estimada", value: 23.8, unit: "%", formatted_value: "23.8%", reference_min: 21.8, reference_max: 25.8, status: "adequate", hint: "21.8% a 25.8%" },
    ],
    goal_metrics: [],
    comparison_rows: [
      { key: "weight_kg", label: "Peso", unit: "kg", previous_value: 85.7, current_value: 84.5, previous_formatted: "85.7 kg", current_formatted: "84.5 kg", difference_absolute: -1.2, difference_percent: -1.4, trend: "down" },
      { key: "body_fat_used_percent", label: "Gordura estimada", unit: "%", previous_value: 25.6, current_value: 23.8, previous_formatted: "25.6%", current_formatted: "23.8%", difference_absolute: -1.8, difference_percent: -7.3, trend: "down" },
    ],
    history_series: [],
    insights: [
      {
        key: "fat_down_muscle_stable",
        title: "Reducao de gordura com preservacao muscular",
        message: "A estimativa por medidas indica melhora de composicao corporal com massa muscular preservada.",
        tone: "positive",
        reasons: ["gordura estimada reduziu", "massa muscular preservada"],
      },
    ],
    teacher_notes: "Medidas realizadas pelo professor na mesma rotina operacional.",
    methodological_note:
      "O percentual de gordura exibido neste relatorio e uma estimativa calculada a partir de medidas corporais quando configurado pelo profissional. Ele nao substitui avaliacao clinica.",
    segmental_analysis_available: false,
  };
}

async function mockAuth(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "owner-1",
        gym_id: "11111111-1111-1111-1111-111111111111",
        full_name: "Owner Teste",
        email: "owner@test.com",
        role: "owner",
        is_active: true,
        created_at: "2026-04-14T10:00:00Z",
      }),
    }),
  );

  await page.addInitScript(() => {
    localStorage.setItem("ai_gym_access_token", "token");
  });
}

test("body composition report shows anthropometry as official source", async ({ page }) => {
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  await mockAuth(page);

  await page.route("**/api/v1/members/member-1/body-composition/eval-1/report", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(bodyCompositionReport()),
    }),
  );

  await page.goto("/assessments/members/member-1/body-composition/eval-1/report");

  await expect(page.getByRole("heading", { name: /Erick Bedin/i })).toBeVisible();
  await expect(page.getByText("Fonte oficial da gordura corporal")).toBeVisible();
  await expect(page.getByText("23.8%").first()).toBeVisible();
  await expect(page.getByText("Medidas manuais")).toBeVisible();
  await expect(page.getByText("Bioimpedancia bruta")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Medidas corporais" })).toBeVisible();
  await expect(page.getByText("Abdomen").first()).toBeVisible();
  await expect(page.getByText("Braco direito contraido").first()).toBeVisible();

  await page.screenshot({
    path: `${EVIDENCE_DIR}/body-composition-report-source-panel.png`,
    fullPage: true,
  });
});
