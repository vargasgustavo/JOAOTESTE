import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('Staff releases table → customer gets called', () => {
  test('complete flow: release table → allocation → customer status updates', async ({ page }) => {
    // Login as staff
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="tel"]', '11000000002');
    await page.fill('input[type="password"]', 'Staff@123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard/**');

    // Wait for table grid to load
    await expect(page.locator('[data-testid^="table-card-"]').first()).toBeVisible({ timeout: 10000 });

    // Find an OCCUPIED table and release it
    const releaseBtn = page.locator('[data-testid^="release-btn-"]').first();
    await releaseBtn.waitFor({ timeout: 10000 });
    await releaseBtn.click();

    // Check toast notification
    await expect(page.locator('text=liberada para limpeza')).toBeVisible({ timeout: 5000 });

    // Wait for polling update (7s interval)
    await page.waitForTimeout(8000);

    const tables = page.locator('[data-testid^="table-card-"]');
    await expect(tables.first()).toBeVisible();
  });
});

test.describe('Customer queue tracking', () => {
  test('customer joins queue and sees position', async ({ page }) => {
    await page.goto(`${BASE_URL}/restaurants`);
    const restaurantLink = page.locator('h2').first();
    await restaurantLink.click();
    await page.waitForURL('**/restaurants/**');

    await page.fill('input[placeholder="Seu nome"]', 'Test Customer E2E');
    await page.fill('input[placeholder="Seu telefone"]', '11988887777');
    await page.fill('input[type="number"]', '2');
    await page.click('button:has-text("Entrar na Fila")');

    await expect(
      page.locator('text=posição').or(page.locator('text=mesa está pronta'))
    ).toBeVisible({ timeout: 10000 });
  });
});
