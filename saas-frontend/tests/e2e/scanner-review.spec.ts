import { expect, test } from "@playwright/test";

test("scanner uses a real worker, reviews the selected photo and stops the stream", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/__scanner_test", (route) => route.fulfill({
    contentType: "text/html",
    body: `<html><body><div id="root"></div><script type="module">
      import RefreshRuntime from '/@react-refresh';
      RefreshRuntime.injectIntoGlobalHook(window);
      window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => (type) => type;
      window.__vite_plugin_react_preamble_installed__ = true;
      await import('/src/index.css');
      const React = (await import('/node_modules/.vite/deps/react.js')).default;
      const { createRoot } = (await import('/node_modules/.vite/deps/react-dom_client.js')).default;
      const { GuidedDocumentScanner } = await import('/src/components/assessments/GuidedDocumentScanner.tsx');
      const { bodyCompositionService } = await import('/src/services/bodyCompositionService.ts');
      const canvas = document.createElement('canvas'); canvas.width = 1200; canvas.height = 1600;
      const ctx = canvas.getContext('2d');
      function paint() {
        ctx.fillStyle='#161616'; ctx.fillRect(0,0,1200,1600);
        ctx.fillStyle='#eeeeee'; ctx.fillRect(260,75,680,1450);
        ctx.fillStyle='#232323';
        for(let y=100;y<1500;y+=60) ctx.fillRect(330,y,540,15);
      }
      paint(); window.scannerStream = canvas.captureStream(20);
      const timer = setInterval(paint,50);
      navigator.mediaDevices.getUserMedia = async () => window.scannerStream;
      navigator.mediaDevices.enumerateDevices = async () => [];
      window.ImageCapture = undefined;
      bodyCompositionService.recordCaptureEvent = async () => {};
      bodyCompositionService.prepareImage = async (_id,file) => ({ blob:file, metadata:{
        corners:[{x:.22,y:.05},{x:.78,y:.05},{x:.78,y:.95},{x:.22,y:.95}],
        confidence:.9, method:'perspective',quality_codes:[],quality_metrics:{},
        source_width:1200,source_height:1600,output_width:1200,output_height:1600
      }});
      window.confirmed = null;
      function App() {
        const [open,setOpen]=React.useState(true);
        return React.createElement(GuidedDocumentScanner,{memberId:'synthetic',open,
          onClose:()=>{setOpen(false);clearInterval(timer)},onConfirm:(_file,metadata)=>window.confirmed=metadata});
      }
      createRoot(document.getElementById('root')).render(React.createElement(App));
    </script></body></html>`,
  }));
  await page.goto("/__scanner_test");
  await expect(page.getByRole("button", { name: "Fotografar agora" })).toBeEnabled().catch((error) => { throw new Error(`${String(error)}; browser errors: ${errors.join("; ")}`); });
  await expect.poll(() => page.workers().length).toBe(1);
  await page.getByRole("button", { name: "Fotografar agora" }).click();
  await expect(page.getByRole("button", { name: "Confirmar foto corrigida" })).toBeEnabled();
  await expect.poll(() => page.evaluate(() => (window as unknown as { scannerStream: MediaStream }).scannerStream.getTracks().every((track) => track.readyState === "ended"))).toBe(true);
  await page.getByRole("button", { name: "Original", exact: true }).click();
  await page.getByRole("button", { name: "Girar direita" }).click();
  await page.getByRole("button", { name: "Ajustar quatro cantos" }).click();
  await expect(page.getByRole("button", { name: "Confirmar foto original" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Ajustar canto topLeft" })).toBeVisible();
  await page.getByRole("button", { name: "Cancelar ajuste" }).click();
  await page.getByRole("button", { name: "Confirmar foto original" }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { confirmed: { correction_confirmed: boolean } | null }).confirmed?.correction_confirmed)).toBe(false);
  await expect(page.getByRole("dialog")).not.toBeVisible();
  expect(errors).toEqual([]);
});
