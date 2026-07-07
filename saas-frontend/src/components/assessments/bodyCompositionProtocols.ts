export type BodyCompositionProtocol = {
  key: string;
  label: string;
  sex: "male" | "female" | null;
  ageMin: number | null;
  ageMax: number | null;
  requiredFields: string[];
  supported: boolean;
  notes?: string;
};

export const SKINFOLD_FIELD_LABELS: Record<string, string> = {
  skinfold_chest_mm: "Dobra peitoral",
  skinfold_midaxillary_mm: "Dobra axilar media",
  skinfold_subscapular_mm: "Dobra subescapular",
  skinfold_triceps_mm: "Dobra tricipital",
  skinfold_biceps_mm: "Dobra bicipital",
  skinfold_abdominal_mm: "Dobra abdominal",
  skinfold_suprailiac_mm: "Dobra suprailiaca",
  skinfold_thigh_mm: "Dobra coxa",
  skinfold_calf_mm: "Dobra panturrilha",
  waist_cm: "Cintura",
  weight_kg: "Peso",
};

export const BODY_COMPOSITION_PROTOCOLS: BodyCompositionProtocol[] = [
  { key: "manual_bioimpedance", label: "Adicionar manualmente (Balanca de Bioimpedancia)", sex: null, ageMin: null, ageMax: null, requiredFields: [], supported: false, notes: "Registro manual ou dado bruto da bioimpedancia." },
  { key: "mcardle_1992_4_male_18_34", label: "Macardle (1992) 4 dobras - Homens, 18-34 anos", sex: "male", ageMin: 18, ageMax: 34, requiredFields: ["skinfold_chest_mm", "skinfold_abdominal_mm", "skinfold_thigh_mm", "skinfold_suprailiac_mm"], supported: false },
  { key: "mcardle_1992_3_female_18_48", label: "Macardle (1992) 3 dobras - Mulheres, 18-48 anos", sex: "female", ageMin: 18, ageMax: 48, requiredFields: ["skinfold_abdominal_mm", "skinfold_triceps_mm", "skinfold_suprailiac_mm"], supported: false },
  { key: "jackson_pollock_7_female_18_55", label: "Jackson et al. (1980), 7 dobras - Mulheres negras ou hispanicas, 18-55 anos", sex: "female", ageMin: 18, ageMax: 55, requiredFields: ["skinfold_chest_mm", "skinfold_midaxillary_mm", "skinfold_subscapular_mm", "skinfold_triceps_mm", "skinfold_abdominal_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm"], supported: true, notes: "Calculado como Jackson/Pollock/Ward 7 sites publico; revisar populacao antes de usar oficialmente." },
  { key: "jackson_pollock_7_male_18_61", label: "Jackson e Pollock (1978), 7 dobras - Homens negros ou atletas, 18-61 anos", sex: "male", ageMin: 18, ageMax: 61, requiredFields: ["skinfold_chest_mm", "skinfold_midaxillary_mm", "skinfold_subscapular_mm", "skinfold_triceps_mm", "skinfold_abdominal_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm"], supported: true, notes: "Calculado como Jackson/Pollock 7 sites publico; revisar populacao antes de usar oficialmente." },
  { key: "jackson_pollock_3_female_18_55", label: "Jackson et al. (1980), 3 dobras - Mulheres brancas, 18-55 anos", sex: "female", ageMin: 18, ageMax: 55, requiredFields: ["skinfold_triceps_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm"], supported: true },
  { key: "jackson_pollock_3_male_18_61", label: "Jackson e Pollock (1978), 3 dobras - Homens brancos, 18-61 anos", sex: "male", ageMin: 18, ageMax: 61, requiredFields: ["skinfold_chest_mm", "skinfold_abdominal_mm", "skinfold_thigh_mm"], supported: true },
  { key: "pollock_1980_7_female_18_61", label: "Pollock et al. (1980), 7 dobras - Mulheres adultas, 18-61 anos", sex: "female", ageMin: 18, ageMax: 61, requiredFields: ["skinfold_chest_mm", "skinfold_midaxillary_mm", "skinfold_subscapular_mm", "skinfold_triceps_mm", "skinfold_abdominal_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm"], supported: true },
  { key: "pollock_1980_7_male_18_61", label: "Pollock et al. (1980), 7 dobras - Homens adultos, 18-61 anos", sex: "male", ageMin: 18, ageMax: 61, requiredFields: ["skinfold_chest_mm", "skinfold_midaxillary_mm", "skinfold_subscapular_mm", "skinfold_triceps_mm", "skinfold_abdominal_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm"], supported: true },
  { key: "guedes_1985_3_female_18_30", label: "Guedes (1985), 3 dobras - Mulheres, 18-30 anos", sex: "female", ageMin: 18, ageMax: 30, requiredFields: ["skinfold_subscapular_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm"], supported: false },
  { key: "guedes_1985_3_male_18_30", label: "Guedes (1985), 3 dobras - Homens, 18-30 anos", sex: "male", ageMin: 18, ageMax: 30, requiredFields: ["skinfold_triceps_mm", "skinfold_suprailiac_mm", "skinfold_abdominal_mm"], supported: false },
  { key: "petroski_1995_female_18_51", label: "Petroski (1995), Mulheres, 18-51 anos", sex: "female", ageMin: 18, ageMax: 51, requiredFields: ["skinfold_triceps_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm", "skinfold_calf_mm"], supported: false },
  { key: "petroski_1995_male_18_66", label: "Petroski (1995), Homens, 18-66 anos", sex: "male", ageMin: 18, ageMax: 66, requiredFields: ["skinfold_subscapular_mm", "skinfold_triceps_mm", "skinfold_suprailiac_mm", "skinfold_calf_mm"], supported: true, notes: "Densidade corporal Petroski masculino 4 dobras; convertido por Siri." },
  { key: "durnin_womersley_1974_female_18_68", label: "Durnin & Womersley (1974), Mulheres, 18-68 anos. Generalizada", sex: "female", ageMin: 18, ageMax: 68, requiredFields: ["skinfold_triceps_mm", "skinfold_biceps_mm", "skinfold_subscapular_mm", "skinfold_suprailiac_mm"], supported: true },
  { key: "durnin_womersley_1974_male_17_72", label: "Durnin & Womersley (1974), Homens, 17-72 anos. Generalizada", sex: "male", ageMin: 17, ageMax: 72, requiredFields: ["skinfold_triceps_mm", "skinfold_biceps_mm", "skinfold_subscapular_mm", "skinfold_suprailiac_mm"], supported: true },
  { key: "weltman_1988_female_obese_20_60", label: "Weltman et col. (1988), Mulheres obesas, 20-60 anos", sex: "female", ageMin: 20, ageMax: 60, requiredFields: ["waist_cm", "weight_kg"], supported: false },
  { key: "weltman_1988_male_obese_20_60", label: "Weltman et col. (1988), Homens obesos, 20-60 anos", sex: "male", ageMin: 20, ageMax: 60, requiredFields: ["waist_cm", "weight_kg"], supported: false },
  { key: "slaughter_1988_boys_black_white_6_17", label: "Slaughter et al. (1988), Meninos negros ou brancos, 6-17 anos", sex: "male", ageMin: 6, ageMax: 17, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false, notes: "Requer maturacao/ramificacao populacional; manual review em V1." },
  { key: "slaughter_1988_girls_black_white_6_17", label: "Slaughter et al. (1988), Meninas negras ou brancas, 6-17 anos", sex: "female", ageMin: 6, ageMax: 17, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false, notes: "Requer maturacao/ramificacao populacional; manual review em V1." },
  { key: "guedes_1985_boys_white_prepuberal_6_11", label: "Guedes (1985), Rapazes brancos pre-pubere, 6-11 anos", sex: "male", ageMin: 6, ageMax: 11, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "guedes_1985_boys_white_puberal_12_16", label: "Guedes (1985), Rapazes brancos pubere, 12-16 anos", sex: "male", ageMin: 12, ageMax: 16, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "guedes_1985_boys_white_postpuberal_17_18", label: "Guedes (1985), Rapazes brancos pos-pubere, 17-18 anos", sex: "male", ageMin: 17, ageMax: 18, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "guedes_1985_boys_black_prepuberal_6_11", label: "Guedes (1985), Rapazes negros pre-pubere, 6-11 anos", sex: "male", ageMin: 6, ageMax: 11, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "guedes_1985_boys_black_puberal_12_16", label: "Guedes (1985), Rapazes negros pubere, 12-16 anos", sex: "male", ageMin: 12, ageMax: 16, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "guedes_1985_boys_black_postpuberal_17_18", label: "Guedes (1985), Rapazes negros pos-pubere, 17-18 anos", sex: "male", ageMin: 17, ageMax: 18, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "guedes_1985_girls_sum_under_35", label: "Guedes (1985), Mocas (Soma das dobras < 35mm)", sex: "female", ageMin: 6, ageMax: 18, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "slaughter_1988_boys", label: "Slaughter et al. (1988), Meninos", sex: "male", ageMin: 6, ageMax: 17, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "slaughter_1988_girls", label: "Slaughter et al. (1988), Meninas", sex: "female", ageMin: 6, ageMax: 17, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "mcardle_1992_female_9_12", label: "Macardle (1992), Mulheres, 9-12 anos", sex: "female", ageMin: 9, ageMax: 12, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "mcardle_1992_female_13_16", label: "Macardle (1992), Mulheres, 13-16 anos", sex: "female", ageMin: 13, ageMax: 16, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "mcardle_1992_male_9_12", label: "Macardle (1992), Homens, 9-12 anos", sex: "male", ageMin: 9, ageMax: 12, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "mcardle_1992_male_13_16", label: "Macardle (1992), Homens, 13-16 anos", sex: "male", ageMin: 13, ageMax: 16, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"], supported: false },
  { key: "faulkner_1968_male_20_30", label: "Faulkner (1968), Homens, 20-30 anos", sex: "male", ageMin: 20, ageMax: 30, requiredFields: ["skinfold_triceps_mm", "skinfold_subscapular_mm", "skinfold_suprailiac_mm", "skinfold_abdominal_mm"], supported: false },
];

export function getBodyCompositionProtocol(key: string | null | undefined): BodyCompositionProtocol | null {
  if (!key) return null;
  return BODY_COMPOSITION_PROTOCOLS.find((protocol) => protocol.key === key) ?? null;
}
