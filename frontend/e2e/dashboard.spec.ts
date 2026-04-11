import { test, expect } from '@playwright/test';

test('dashboard loads and shows Apex branding', async ({ page }) => {
  await page.goto('/');
  // Should show the app title or key dashboard element
  await expect(page).toHaveTitle(/Apex/i);
});

test('sidebar navigation links are present', async ({ page }) => {
  await page.goto('/');
  // Check at least one nav link exists
  await expect(page.locator('nav a, aside a').first()).toBeVisible();
});
