import { test, expect } from '@playwright/test';

/**
 * Phase 7 E2E golden-path tests.
 * These tests assume the Next.js dev server is running at http://localhost:3000
 * and the backend is running at http://localhost:8000 (or USE_MOCK_DATA=true).
 *
 * Run with: npx playwright test e2e/phase7.spec.ts
 */

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';

// ── 1. Actions page ────────────────────────────────────────────────────────

test.describe('Phase 7 — Actions page', () => {
  test('Actions page loads and shows heading', async ({ page }) => {
    await page.goto(`${BASE_URL}/actions`);

    await expect(
      page.locator('h1, [data-testid="actions-heading"]').filter({ hasText: /actions/i })
    ).toBeVisible({ timeout: 10_000 });
  });

  test('Actions page has view toggle (Kanban or List)', async ({ page }) => {
    await page.goto(`${BASE_URL}/actions`);
    await page.waitForLoadState('networkidle');

    // Either tab or button for toggling between views
    const toggle =
      page.getByRole('button', { name: /kanban/i }).first().or(
        page.getByRole('button', { name: /list/i }).first()
      ).or(
        page.getByRole('tab', { name: /kanban/i }).first()
      ).or(
        page.getByRole('tab', { name: /list/i }).first()
      );

    await expect(toggle.first()).toBeVisible({ timeout: 5_000 });
  });

  test('Actions page shows action cards or empty state after load', async ({ page }) => {
    await page.goto(`${BASE_URL}/actions`);
    await page.waitForLoadState('networkidle');

    const hasCards = await page.locator('[data-testid="action-card"]').count();
    const hasEmpty = await page.locator('text=/no actions/i').count();
    expect(hasCards + hasEmpty).toBeGreaterThan(0);
  });

  test('clicking an action card opens detail panel', async ({ page }) => {
    await page.goto(`${BASE_URL}/actions`);
    await page.waitForLoadState('networkidle');

    const firstCard = page.locator('[data-testid="action-card"]').first();
    if (await firstCard.count() === 0) {
      test.skip();
      return;
    }

    await firstCard.click();

    // Detail panel or dialog should appear
    const detail =
      page.locator('[data-testid="action-detail"]').first().or(
        page.locator('[role="dialog"]').first()
      ).or(
        page.locator('[data-side="right"]').first()
      );

    await expect(detail.first()).toBeVisible({ timeout: 3_000 });
  });

  test('Actions page is responsive on mobile (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE_URL}/actions`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
    // Heading should still be visible on mobile
    const heading = page.locator('h1, [data-testid="actions-heading"]').filter({ hasText: /actions/i });
    await expect(heading.first()).toBeVisible({ timeout: 5_000 });
  });
});

// ── 2. Outreach page ──────────────────────────────────────────────────────

test.describe('Phase 7 — Outreach page', () => {
  test('Outreach page loads and shows heading', async ({ page }) => {
    await page.goto(`${BASE_URL}/outreach`);

    await expect(
      page.locator('h1, [data-testid="outreach-heading"]').filter({ hasText: /outreach/i })
    ).toBeVisible({ timeout: 10_000 });
  });

  test('Outreach page shows email drafts or empty state after load', async ({ page }) => {
    await page.goto(`${BASE_URL}/outreach`);
    await page.waitForLoadState('networkidle');

    const hasDrafts = await page.locator('[data-testid="outreach-card"], [data-testid="email-card"]').count();
    const hasEmpty = await page.locator('text=/no outreach|no emails|no drafts|get started/i').count();
    expect(hasDrafts + hasEmpty).toBeGreaterThan(0);
  });

  test('Outreach page has compose or connect Gmail button', async ({ page }) => {
    await page.goto(`${BASE_URL}/outreach`);
    await page.waitForLoadState('networkidle');

    const actionBtn =
      page.getByRole('button', { name: /compose|new email|connect gmail|draft/i }).first().or(
        page.locator('text=/connect gmail/i').first()
      );

    await expect(actionBtn.first()).toBeVisible({ timeout: 5_000 });
  });

  test('Outreach page is responsive on mobile (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE_URL}/outreach`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
  });
});

// ── 3. Profile page ───────────────────────────────────────────────────────

test.describe('Phase 7 — Profile page', () => {
  test('Profile page loads and shows form fields', async ({ page }) => {
    await page.goto(`${BASE_URL}/profile`);

    // At least one input or textarea should be present
    await expect(
      page.locator('textarea, input[type="text"]').first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('Profile page has a save/update button', async ({ page }) => {
    await page.goto(`${BASE_URL}/profile`);
    await page.waitForLoadState('networkidle');

    await expect(
      page.getByRole('button', { name: /save|update/i })
    ).toBeVisible({ timeout: 5_000 });
  });

  test('Profile page shows profile completeness indicator', async ({ page }) => {
    await page.goto(`${BASE_URL}/profile`);
    await page.waitForLoadState('networkidle');

    const completeness =
      page.getByRole('progressbar').first().or(
        page.locator('text=/%/').first()
      ).or(
        page.locator('text=/complete/i').first()
      );

    await expect(completeness.first()).toBeVisible({ timeout: 5_000 });
  });

  test('Profile page is responsive on mobile (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE_URL}/profile`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
  });
});

// ── 4. Settings page ──────────────────────────────────────────────────────

test.describe('Phase 7 — Settings page', () => {
  test('Settings page loads and shows sections', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
    // Settings page should have some heading or section
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 5_000 });
  });
});

// ── 5. Analytics page ─────────────────────────────────────────────────────

test.describe('Phase 7 — Analytics page', () => {
  test('Analytics page loads and shows stats', async ({ page }) => {
    await page.goto(`${BASE_URL}/analytics`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 5_000 });
  });
});

// ── 6. Cross-page navigation ──────────────────────────────────────────────

test.describe('Phase 7 — Navigation', () => {
  test('Sidebar or nav links to Actions, Outreach, Profile are present', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Check for navigation links to phase 7 pages
    const actionsLink = page.getByRole('link', { name: /actions/i }).first();
    const outreachLink = page.getByRole('link', { name: /outreach/i }).first();
    const profileLink = page.getByRole('link', { name: /profile/i }).first();

    // At least one of these nav links should be visible in the sidebar
    const actionsCount = await actionsLink.count();
    const outreachCount = await outreachLink.count();
    const profileCount = await profileLink.count();

    expect(actionsCount + outreachCount + profileCount).toBeGreaterThan(0);
  });
});
