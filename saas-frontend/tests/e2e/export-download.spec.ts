import { expect, test } from "@playwright/test";
for (const kind of ["members", "checkins"]) {
  test(`downloads ${kind} CSV through the actual export service`, async ({ page }) => {
    await page.route(`**/api/v1/exports/${kind}.csv*`, route => route.fulfill({
      contentType: "text/csv", headers: { "Access-Control-Expose-Headers": "Content-Disposition", "Content-Disposition": `attachment; filename="${kind}.csv"` }, body: "full_name;value\nAluno de teste;1\n",
    }));
    await page.route("**/__export_test", route => route.fulfill({contentType:"text/html",body:`
      <button id="download" disabled>Exportar</button><output id="result"></output>
      <script type="module">
        const { importExportService } = await import('/src/services/importExportService.ts');
        document.getElementById('download').disabled=false;
        document.getElementById('download').onclick = async () => {
          try { await importExportService.${kind === "members" ? "exportMembersCsv" : "exportCheckinsCsv"}(); document.getElementById('result').textContent='Concluido'; }
          catch(e) { document.getElementById('result').textContent=e.message; }
        };
      </script>`}));
    await page.goto("/__export_test");
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(`${kind}.csv`);
    expect(await download.failure()).toBeNull();
    await expect(page.locator("output")).toHaveText("Concluido");
  });
}
