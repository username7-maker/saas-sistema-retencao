ACTUAR_SELECTORS = {
    "login_username": 'input[name="username"], input[name="user"], input[type="text"]',
    "login_password": 'input[name="password"], input[type="password"]',
    "login_submit": 'button[type="submit"], button:has-text("Entrar"), input[type="submit"]',
    "member_search_input": 'input[name="search"], input[name="member_search"], input[placeholder*="Aluno"], input[placeholder*="Buscar"]',
    "member_search_submit": 'button:has-text("Buscar"), button:has-text("Pesquisar"), button[type="submit"]',
    "member_result_row": '[data-testid="member-result"], table tbody tr, .member-row',
    "member_result_name": '[data-testid="member-name"], .member-name, td:first-child',
    "member_result_birthdate": '[data-testid="member-birthdate"], .member-birthdate, td:nth-child(2)',
    "member_result_document": '[data-testid="member-document"], .member-document, td:nth-child(3)',
    "member_result_open": 'a, button',
    "body_composition_tab": 'a:has-text("Bioimped"), a:has-text("Compos"), button:has-text("Bioimped"), button:has-text("Compos")',
    "body_composition_form": 'form, [data-testid="body-composition-form"]',
    "save_button": 'button:has-text("Salvar"), button[type="submit"], input[type="submit"]',
}

ACTUAR_FIELD_SELECTORS = {
    "evaluation_date": 'input[name="evaluation_date"], input[name="date"], input[type="date"]',
    "weight": 'input[name="weight"], input[name="weight_kg"]',
    "body_fat_percent": 'input[name="body_fat_percent"], input[name="fat_pct"], input[name="bodyFat"]',
    "lean_mass_kg": 'input[name="lean_mass_kg"], input[name="fat_free_mass_kg"]',
    "muscle_mass_kg": 'input[name="muscle_mass_kg"], input[name="skeletal_muscle_kg"]',
    "bmi": 'input[name="bmi"]',
    "body_water_percent": 'input[name="body_water_percent"], input[name="water_pct"]',
    "notes": 'textarea[name="notes"], textarea',
}
