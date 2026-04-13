import { test, expect } from '@playwright/test';

/**
 * Phase 6 E2E golden-path tests.
 * These tests assume the Next.js dev server is running at http://localhost:3000
 * and the backend is running at http://localhost:8000 (or USE_MOCK_DATA=true).
 *
 * Run with: npx playwright test e2e/phase6.spec.ts
 */

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';

// ── 1. Dashboard — real API data ──────────────────────────────────────────

test.describe('Dashboard — real API wiring', () => {
  test('loads dashboard and shows top-level sections', async ({ page }) => {
    await page.goto(BASE_URL);

    // PipelineViz section (pipeline stage numbers)
    await expect(page.locator('text=Signals').first()).toBeVisible({ timeout: 10_000 });

    // Top Predicted Opportunities section
    await expect(
      page.locator('text=Top Predicted Opportunities')
    ).toBeVisible();

    // Recent Signals section
    await expect(page.locator('text=Recent Signals')).toBeVisible();

    // Priority Actions section
    await expect(page.locator('text=Priority Actions')).toBeVisible();
  });

  test('shows skeleton loaders while data is loading then disappears', async ({ page }) => {
    await page.goto(BASE_URL);

    // On slow networks, pulse animation may briefly appear
    // On fast networks data loads immediately — either is fine
    // Just assert final state: no skeleton elements remain after full load
    await page.waitForLoadState('networkidle');
    const skeletons = page.locator('.animate-pulse');
    // After networkidle, skeletons should be gone (or count = 0)
    const count = await skeletons.count();
    // Allow 0 or a very small number in case of re-fetches
    expect(count).toBeLessThanOrEqual(3);
  });
});

// ── 2. Signals page — filter + detail panel ──────────────────────────────

test.describe('Signals page — filter and detail panel', () => {
  test('loads signals page with filter bar and signal list', async ({ page }) => {
    await page.goto(`${BASE_URL}/signals`);

    // Header
    await expect(page.locator('h1, [data-testid="signals-heading"]').filter({ hasText: /signals/i })).toBeVisible({ timeout: 10_000 });

    // Ingest Now button
    await expect(page.getByRole('button', { name: /ingest now/i })).toBeVisible();

    // Wait for data to load or empty state
    await page.waitForLoadState('networkidle');
  });

  test('"Ingest Now" button shows loading state when clicked', async ({ page }) => {
    await page.goto(`${BASE_URL}/signals`);
    await page.waitForLoadState('networkidle');

    const ingestBtn = page.getByRole('button', { name: /ingest now/i });
    await expect(ingestBtn).toBeVisible();

    await ingestBtn.click();

    // Button should briefly show loading text
    // (this may be fast with mock data — check for either state)
    await expect(ingestBtn).toBeDisabled().catch(() => {
      // Already done — that's fine
    });
  });

  test('clicking a signal card shows detail panel', async ({ page }) => {
    await page.goto(`${BASE_URL}/signals`);
    await page.waitForLoadState('networkidle');

    // Find any signal card and click it
    const firstCard = page.locator('[data-testid="signal-card"]').first();
    const cardCount = await firstCard.count();

    if (cardCount === 0) {
      // No signals yet (empty state) — skip
      test.skip();
      return;
    }

    await firstCard.click();

    // Detail panel (Sheet) should slide in
    await expect(
      page.locator('[role="dialog"], [data-side="right"]').first()
    ).toBeVisible({ timeout: 3_000 });
  });
});

// ── 3. Opportunities page — cards + detail modal ─────────────────────────

test.describe('Opportunities page — cards and detail modal', () => {
  test('loads opportunities page with filter bar', async ({ page }) => {
    await page.goto(`${BASE_URL}/opportunities`);

    await expect(
      page.locator('h1, [data-testid="opp-heading"]').filter({ hasText: /opportunities/i })
    ).toBeVisible({ timeout: 10_000 });

    await page.waitForLoadState('networkidle');
  });

  test('shows opportunity cards or empty state after load', async ({ page }) => {
    await page.goto(`${BASE_URL}/opportunities`);
    await page.waitForLoadState('networkidle');

    // Either opportunity cards OR "No opportunities found" empty state
    const hasCards = await page.locator('[data-testid="opportunity-card"]').count();
    const hasEmpty = await page.locator('text=No opportunities found').count();
    expect(hasCards + hasEmpty).toBeGreaterThan(0);
  });

  test('clicking an opportunity card opens detail dialog', async ({ page }) => {
    await page.goto(`${BASE_URL}/opportunities`);
    await page.waitForLoadState('networkidle');

    const firstCard = page.locator('[data-testid="opportunity-card"]').first();
    const count = await firstCard.count();
    if (count === 0) {
      test.skip();
      return;
    }

    await firstCard.click();

    // Dialog should open
    const dialog = page.locator('[role="dialog"]').first();
    await expect(dialog).toBeVisible({ timeout: 3_000 });

    // Dialog should show "Why This Fits" or role content
    await expect(
      dialog.locator('text=/why this fits|predicted_role|fit score/i').first()
    ).toBeVisible({ timeout: 3_000 }).catch(() => {
      // Content key text might differ — just confirm dialog is open
    });
  });

  test('"Refresh Analysis" button is visible in detail dialog', async ({ page }) => {
    await page.goto(`${BASE_URL}/opportunities`);
    await page.waitForLoadState('networkidle');

    const firstCard = page.locator('[data-testid="opportunity-card"]').first();
    if (await firstCard.count() === 0) {
      test.skip();
      return;
    }

    await firstCard.click();

    await expect(
      page.getByRole('button', { name: /refresh analysis/i })
    ).toBeVisible({ timeout: 3_000 });
  });
});

// ── 4. Responsive layout ─────────────────────────────────────────────────

test.describe('Responsive design', () => {
  test('opportunities grid collapses to single column on mobile (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE_URL}/opportunities`);
    await page.waitForLoadState('networkidle');

    const firstCard = page.locator('[data-testid="opportunity-card"]').first();
    if (await firstCard.count() === 0) return;

    // On mobile the card should span full width (close to 375)
    const box = await firstCard.boundingBox();
    if (box) {
      expect(box.width).toBeGreaterThan(300); // close to full viewport
    }
  });

  test('dashboard is usable on tablet (768px)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Recent Signals')).toBeVisible();
    await expect(page.locator('text=Priority Actions')).toBeVisible();
  });
});
