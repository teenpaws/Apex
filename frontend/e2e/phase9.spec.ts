import { test, expect } from '@playwright/test';

/**
 * Phase 9 E2E comprehensive spec — all 8 pages, golden-path journey, performance.
 * Assumes Next.js dev server at http://localhost:3000 and backend at http://localhost:8000
 * (USE_MOCK_DATA=true is sufficient — no real DB or API keys needed).
 *
 * Run with: npx playwright test e2e/phase9.spec.ts --reporter=list
 */

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';

const ALL_PAGES = [
  { path: '/', name: 'Dashboard' },
  { path: '/signals', name: 'Signals' },
  { path: '/opportunities', name: 'Opportunities' },
  { path: '/actions', name: 'Actions' },
  { path: '/outreach', name: 'Outreach' },
  { path: '/profile', name: 'Profile' },
  { path: '/analytics', name: 'Analytics' },
  { path: '/settings', name: 'Settings' },
];

// ── Section 1: All 8 pages load without fatal JS errors ──────────────────────

test.describe('Phase 9 — All pages load without console errors', () => {
  for (const { path, name } of ALL_PAGES) {
    test(`${name} page loads without JS errors`, async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });

      await page.goto(`${BASE_URL}${path}`);
      await page.waitForLoadState('networkidle');

      // Filter known non-fatal React noise
      const fatalErrors = consoleErrors.filter(
        (e) =>
          !e.includes('Warning:') &&
          !e.includes('warning:') &&
          !e.includes('Download the React DevTools')
      );
      expect(
        fatalErrors,
        `Console errors on ${name}: ${fatalErrors.join(', ')}`
      ).toHaveLength(0);
    });
  }
});

// ── Section 2: All 8 pages render meaningful content (no blank / 500 screens) ─

test.describe('Phase 9 — All pages render content', () => {
  for (const { path, name } of ALL_PAGES) {
    test(`${name} page renders visible content`, async ({ page }) => {
      await page.goto(`${BASE_URL}${path}`);
      await page.waitForLoadState('networkidle');

      // Body must be present
      await expect(page.locator('body')).toBeVisible();

      // Must NOT be a 500 or generic error screen (use h2 selector to avoid matching "$500M" in content)
      const h2texts = await page.locator('h2').allTextContents();
      const hasErrorHeading = h2texts.some((t) => t.trim() === '500' || /internal server error/i.test(t));
      expect(hasErrorHeading, `${name} must not show a 500 error heading`).toBe(false);
      await expect(page.locator('text=Internal Server Error')).not.toBeVisible();
      await expect(page.locator('text=Application error')).not.toBeVisible();

      // At least one heading (h1 or h2) must exist
      const headingCount = await page.locator('h1, h2').count();
      expect(headingCount, `${name} must have at least one heading`).toBeGreaterThan(0);
    });
  }
});

// ── Section 3: Dashboard real API wiring ─────────────────────────────────────

test.describe('Phase 9 — Dashboard real data wiring', () => {
  test('PipelineViz displays Pipeline Overview section with all four stage labels', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // PipelineViz section header
    await expect(page.locator('text=Pipeline Overview')).toBeVisible({ timeout: 10_000 });

    // All four pipeline stage labels must appear somewhere on the page
    await expect(page.locator('text=Signals').first()).toBeVisible();
    await expect(page.locator('text=Opportunities').first()).toBeVisible();
    await expect(page.locator('text=Actions').first()).toBeVisible();
    await expect(page.locator('text=Outreach').first()).toBeVisible();
  });

  test('Dashboard shows Top Predicted Opportunities section', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('text=Top Predicted Opportunities')).toBeVisible({ timeout: 10_000 });
  });

  test('Dashboard shows Recent Signals section', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('text=Recent Signals')).toBeVisible({ timeout: 10_000 });
  });

  test('Dashboard shows Priority Actions section', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('text=Priority Actions')).toBeVisible({ timeout: 10_000 });
  });

  test('Dashboard skeleton loaders resolve after networkidle', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const skeletons = page.locator('.animate-pulse');
    const count = await skeletons.count();
    // Skeletons should be gone (or a trivially small residual count) after load
    expect(count, 'Skeleton loaders should be gone after networkidle').toBeLessThanOrEqual(3);
  });
});

// ── Section 4: Analytics page real data wiring ───────────────────────────────

test.describe('Phase 9 — Analytics page', () => {
  test('Analytics page shows the Analytics heading', async ({ page }) => {
    await page.goto(`${BASE_URL}/analytics`);
    await expect(page.locator('h1').filter({ hasText: /analytics/i })).toBeVisible({ timeout: 10_000 });
  });

  test('Analytics page shows stat cards with correct labels', async ({ page }) => {
    await page.goto(`${BASE_URL}/analytics`);
    await page.waitForLoadState('networkidle');

    // These labels are hardcoded in StatCard — they appear once data arrives
    await expect(page.locator('text=Signals this week')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('text=New opportunities')).toBeVisible();
    await expect(page.locator('text=Actions completed')).toBeVisible();
    await expect(page.locator('text=Agent cost this month')).toBeVisible();
  });

  test('Analytics page shows Signal Velocity chart section', async ({ page }) => {
    await page.goto(`${BASE_URL}/analytics`);
    await expect(
      page.locator('text=Signal Velocity (last 30 days)')
    ).toBeVisible({ timeout: 10_000 });
  });

  test('Analytics page shows Top Companies by Signal Count chart section', async ({ page }) => {
    await page.goto(`${BASE_URL}/analytics`);
    await expect(
      page.locator('text=Top Companies by Signal Count')
    ).toBeVisible({ timeout: 10_000 });
  });

  test('Analytics page shows Conversion Pipeline section (from API data)', async ({ page }) => {
    await page.goto(`${BASE_URL}/analytics`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Conversion Pipeline')).toBeVisible({ timeout: 10_000 });
  });

  test('Analytics page shows Agent Cost Breakdown section', async ({ page }) => {
    await page.goto(`${BASE_URL}/analytics`);
    await expect(page.locator('text=Agent Cost Breakdown')).toBeVisible({ timeout: 10_000 });
  });

  test('Analytics Agent Cost Breakdown shows empty state when no runs recorded', async ({ page }) => {
    await page.goto(`${BASE_URL}/analytics`);
    await page.waitForLoadState('networkidle');

    // Mock mode returns empty runs array — empty state message must show
    await expect(
      page.locator('text=No agent runs recorded yet.')
    ).toBeVisible({ timeout: 10_000 });
  });
});

// ── Section 5: Settings page ─────────────────────────────────────────────────

test.describe('Phase 9 — Settings page', () => {
  test('Settings page shows the Settings heading', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1').filter({ hasText: /settings/i })).toBeVisible({ timeout: 10_000 });
  });

  test('Settings page shows API Key Status section', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=API Key Status')).toBeVisible({ timeout: 10_000 });
  });

  test('Settings page shows Signal Sources section with toggle switches', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=Signal Sources')).toBeVisible({ timeout: 10_000 });

    // At least one toggle switch must be present
    const toggles = page.locator('[role="switch"]');
    await expect(toggles.first()).toBeVisible({ timeout: 5_000 });
  });

  test('Settings page shows Notifications section', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=Notifications')).toBeVisible({ timeout: 10_000 });
  });

  test('Settings page shows Connected Accounts section with Gmail button', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=Connected Accounts')).toBeVisible({ timeout: 10_000 });

    // Connect Gmail / Reconnect Gmail button
    await expect(
      page.getByRole('button', { name: /connect gmail|reconnect gmail/i })
    ).toBeVisible({ timeout: 5_000 });
  });

  test('Settings page shows ingest frequency radio options', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Hourly')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('text=Every 4h')).toBeVisible();
    await expect(page.locator('text=Daily')).toBeVisible();
  });

  test('Settings toggle can be clicked and changes state', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');

    // Find the first toggle switch
    const toggle = page.locator('[role="switch"]').first();
    await expect(toggle).toBeVisible({ timeout: 5_000 });

    const initialChecked = await toggle.getAttribute('aria-checked');

    await toggle.click();

    // aria-checked should have flipped
    const afterChecked = await toggle.getAttribute('aria-checked');
    expect(afterChecked).not.toEqual(initialChecked);
  });
});

// ── Section 6: Full user journey (golden path) ───────────────────────────────

test.describe('Phase 9 — Full user journey', () => {
  test('User navigates Dashboard → Signals → Opportunities → Actions → Outreach via sidebar', async ({ page }) => {
    // Step 1: Dashboard
    await page.goto(BASE_URL);
    await expect(page.locator('text=Pipeline Overview')).toBeVisible({ timeout: 10_000 });

    // Step 2: Signals
    await page.click('a[href="/signals"]');
    await expect(page).toHaveURL(/signals/);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1').filter({ hasText: /signals/i })).toBeVisible({ timeout: 5_000 });

    // Step 3: Opportunities
    await page.click('a[href="/opportunities"]');
    await expect(page).toHaveURL(/opportunities/);
    await page.waitForLoadState('networkidle');
    await expect(
      page.locator('h1, [data-testid="opp-heading"]').filter({ hasText: /opportunities/i })
    ).toBeVisible({ timeout: 5_000 });

    // Step 4: Actions
    await page.click('a[href="/actions"]');
    await expect(page).toHaveURL(/actions/);
    await page.waitForLoadState('networkidle');
    await expect(
      page.locator('h1, [data-testid="actions-heading"]').filter({ hasText: /actions/i })
    ).toBeVisible({ timeout: 5_000 });

    // Step 5: Outreach
    await page.click('a[href="/outreach"]');
    await expect(page).toHaveURL(/outreach/);
    await page.waitForLoadState('networkidle');
    await expect(
      page.locator('h1, [data-testid="outreach-heading"]').filter({ hasText: /outreach/i })
    ).toBeVisible({ timeout: 5_000 });
  });

  test('User can navigate to Analytics and Settings via sidebar', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Navigate to Analytics
    await page.click('a[href="/analytics"]');
    await expect(page).toHaveURL(/analytics/);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1').filter({ hasText: /analytics/i })).toBeVisible({ timeout: 5_000 });

    // Navigate to Settings
    await page.click('a[href="/settings"]');
    await expect(page).toHaveURL(/settings/);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1').filter({ hasText: /settings/i })).toBeVisible({ timeout: 5_000 });
  });

  test('All sidebar navigation links are present on Dashboard', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const expectedLinks = [
      '/signals',
      '/opportunities',
      '/actions',
      '/outreach',
      '/profile',
      '/analytics',
      '/settings',
    ];

    for (const href of expectedLinks) {
      const link = page.locator(`a[href="${href}"]`);
      const count = await link.count();
      expect(count, `Sidebar link to ${href} must exist`).toBeGreaterThan(0);
    }
  });

  test('Profile page shows form fields and save button (no 500 error)', async ({ page }) => {
    await page.goto(`${BASE_URL}/profile`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('text=500')).not.toBeVisible();
    await expect(page.locator('text=Internal Server Error')).not.toBeVisible();

    // Profile must have at least one input
    const inputCount = await page.locator('textarea, input[type="text"]').count();
    expect(inputCount, 'Profile must have at least one text input or textarea').toBeGreaterThan(0);
  });
});

// ── Section 7: Performance ────────────────────────────────────────────────────

test.describe('Phase 9 — Performance', () => {
  test('Dashboard loads in under 3 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    const elapsed = Date.now() - start;
    expect(elapsed, `Dashboard took ${elapsed}ms (limit: 3000ms)`).toBeLessThan(3_000);
  });

  test('Analytics page loads in under 4 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto(`${BASE_URL}/analytics`);
    await page.waitForLoadState('networkidle');
    const elapsed = Date.now() - start;
    expect(elapsed, `Analytics took ${elapsed}ms (limit: 4000ms)`).toBeLessThan(4_000);
  });

  test('Settings page loads in under 3 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');
    const elapsed = Date.now() - start;
    expect(elapsed, `Settings took ${elapsed}ms (limit: 3000ms)`).toBeLessThan(3_000);
  });
});

// ── Section 8: Responsive design for untested pages ──────────────────────────

test.describe('Phase 9 — Responsive design (Analytics + Settings)', () => {
  test('Analytics page is usable on tablet (768px)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE_URL}/analytics`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('h1').filter({ hasText: /analytics/i })).toBeVisible({ timeout: 5_000 });
  });

  test('Analytics page is usable on mobile (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE_URL}/analytics`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('text=500')).not.toBeVisible();
  });

  test('Settings page is usable on mobile (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
    // At least the heading is visible on mobile
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 5_000 });
  });
});
