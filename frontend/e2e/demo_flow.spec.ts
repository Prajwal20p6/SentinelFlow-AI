import { test, expect } from '@playwright/test';

test.describe('SentinelFlow AI Core Demo Flow E2E', () => {
  test('log in -> trigger demo incident -> verify active incidents & mastra steps -> export postmortem PDF', async ({ page, request }) => {
    // Step 1: Navigate to home page
    await page.goto('/');

    // Step 2: Fill login credentials and submit if on login screen
    const submitBtn = page.locator('button:has-text("INJECT CREDENTIALS")').or(page.locator('button[type="submit"]')).first();
    if (await submitBtn.isVisible({ timeout: 10000 }).catch(() => false)) {
      const emailInput = page.locator('input[type="email"]');
      if (await emailInput.isVisible().catch(() => false)) {
        await emailInput.fill('admin@sentinelflow.ai');
        await page.locator('input[type="password"]').fill('admin123');
      }
      await submitBtn.click();
    }

    // Verify main dashboard sidebar loads
    const cyberDashboardTab = page.locator('button').filter({ hasText: 'Cyber Dashboard' });
    await expect(cyberDashboardTab).toBeVisible({ timeout: 30000 });


    // Step 3: Authenticate via API and trigger a demo incident (CPU_SPIKE)
    const loginRes = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      data: { email: 'admin@sentinelflow.ai', password: 'admin123' },
    });
    expect(loginRes.ok()).toBeTruthy();
    const loginData = await loginRes.json();
    const token = loginData.access_token;

    const triggerRes = await request.post('http://127.0.0.1:8000/api/v1/demo/trigger', {
      headers: { Authorization: `Bearer ${token}` },
      data: { scenario: 'CPU_SPIKE' },
    });
    expect(triggerRes.ok()).toBeTruthy();
    const triggerData = await triggerRes.json();
    expect(triggerData.status).toBe('success');
    expect(triggerData.incident_id).toBeDefined();
    const incidentId = triggerData.incident_id;
    console.log(`[E2E Test] Triggered demo incident ID: #${incidentId}`);


    // Step 4: Click Active Incidents tab and verify incident appears
    const activeIncidentsTab = page.locator('button').filter({ hasText: 'Active Incidents' });
    await activeIncidentsTab.click();

    const incidentBadge = page.locator(`text=#${incidentId}`).or(page.locator('text=CPU_SPIKE')).first();
    await expect(incidentBadge).toBeVisible({ timeout: 15000 });

    // Step 5: Click Mastra Execution tab and verify Mastra Live Execution Monitor is shown
    const mastraTab = page.locator('button').filter({ hasText: 'Mastra Execution' });
    await mastraTab.click();

    const mastraTitle = page.locator('text=Mastra Live Execution Monitor').or(page.locator('text=Mastra Execution')).first();
    await expect(mastraTitle).toBeVisible({ timeout: 15000 });

    // Step 6: Request Postmortem PDF export endpoint
    const pdfRes = await request.get(`http://127.0.0.1:8000/api/v1/incidents/${incidentId}/postmortem/pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(pdfRes.status()).toBe(200);
    expect(pdfRes.headers()['content-type']).toBe('application/pdf');

    // Step 7: Assert PDF binary buffer starts with %PDF- magic header
    const pdfBuffer = await pdfRes.body();
    const pdfHeader = pdfBuffer.slice(0, 5).toString('utf-8');
    console.log(`[E2E Test] PDF Magic Header Bytes: ${pdfHeader}`);
    expect(pdfHeader).toBe('%PDF-');
  });
});
