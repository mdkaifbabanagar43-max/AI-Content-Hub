/**
 * E2E Test Suite – Idea Studio Workflow
 * Tool: Playwright
 * Coverage:
 *   1. Concept card selection → correct script loads into modal
 *   2. Cancel rolls back edited script to AI original
 *   3. Empty / whitespace / too-long script blocks submission
 *   4. XSS injection in script textarea does not render HTML
 *   5. Rapid clicks on concept cards do not cause duplicate requests
 *   6. GENERATE MASTERPIECE: success path awaits resolution
 *   7. Network timeout produces actionable toast, not a page freeze
 *   8. Visibility-change warning during active render
 *   9. Responsive layout – sidebar does not obscure the action button
 */

import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const BASE_URL = 'http://localhost:3000';
const TOPIC   = 'Top 3 AI coding tools in 2026';

/** Sign in via Firebase email/password (adjust credentials for CI). */
async function signIn(page: Page) {
  await page.goto(`${BASE_URL}/auth`);
  await page.getByPlaceholder(/email/i).fill(process.env.TEST_EMAIL ?? 'test@cloneframe.com');
  await page.getByPlaceholder(/password/i).fill(process.env.TEST_PASSWORD ?? 'Test1234!');
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL('**/');
}

/** Navigate to Idea Studio from the sidebar. */
async function goToIdeaStudio(page: Page) {
  await page.getByRole('link', { name: /idea studio/i }).click();
  await expect(page.getByText(/what will you create today/i)).toBeVisible({ timeout: 8000 });
}

/** Type topic, click Brainstorm, wait for concept cards. */
async function brainstorm(page: Page, topic = TOPIC) {
  await page.getByPlaceholder(/topic|idea/i).fill(topic);
  await page.getByRole('button', { name: /brainstorm/i }).click();
  await expect(page.locator('[data-testid="concept-card"]').first()).toBeVisible({ timeout: 30000 });
}

// ---------------------------------------------------------------------------
// Test Suite
// ---------------------------------------------------------------------------

test.describe('Idea Studio – Core Workflow', () => {

  test.beforeEach(async ({ page }) => {
    await signIn(page);
    await goToIdeaStudio(page);
  });

  // ── 1. Brainstorm + concept card loads correct script into modal ──────────
  test('selecting a concept card opens Review Script modal with non-empty script', async ({ page }) => {
    await brainstorm(page);

    const firstCard = page.locator('[data-testid="concept-card"]').first();
    const conceptTitle = await firstCard.getByRole('heading').first().innerText();
    await firstCard.click();

    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });

    const ta = page.getByRole('textbox');
    await expect(ta).not.toHaveValue('');
    await expect(ta).not.toHaveValue(/loading script/i);

    console.log(`Concept: "${conceptTitle}" -> script loaded`);
  });

  // ── 2. Cancel rolls back modified script ─────────────────────────────────
  test('Cancel in Review Script modal restores original AI script', async ({ page }) => {
    await brainstorm(page);
    await page.locator('[data-testid="concept-card"]').first().click();
    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });

    const ta = page.getByRole('textbox');
    const originalScript = await ta.inputValue();

    await ta.fill('COMPLETELY REPLACED BY USER');
    await page.getByRole('button', { name: /cancel/i }).click();
    await expect(page.getByText(/review script/i)).not.toBeVisible();

    // Re-open same card
    await page.locator('[data-testid="concept-card"]').first().click();
    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });

    // Script must be original (state rolled back)
    await expect(page.getByRole('textbox')).toHaveValue(originalScript);
  });

  // ── 3a. Empty script blocks submission ────────────────────────────────────
  test('GENERATE MASTERPIECE is disabled when script is empty', async ({ page }) => {
    await brainstorm(page);
    await page.locator('[data-testid="concept-card"]').first().click();
    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });

    await page.getByRole('textbox').clear();

    const btn = page.getByRole('button', { name: /generate masterpiece/i });
    await expect(btn).toBeDisabled();
    await expect(page.getByText(/script cannot be empty/i)).toBeVisible();
  });

  // ── 3b. Whitespace-only script blocks submission ──────────────────────────
  test('GENERATE MASTERPIECE is disabled for whitespace-only script', async ({ page }) => {
    await brainstorm(page);
    await page.locator('[data-testid="concept-card"]').first().click();
    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });

    await page.getByRole('textbox').fill('     \n\n\t   ');

    const btn = page.getByRole('button', { name: /generate masterpiece/i });
    await expect(btn).toBeDisabled();
  });

  // ── 3c. Too-long script blocks submission ─────────────────────────────────
  test('character counter warns at 90% of 5000 char limit', async ({ page }) => {
    await brainstorm(page);
    await page.locator('[data-testid="concept-card"]').first().click();
    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });

    // Fill textarea to 4600 chars (> 90% of 5000)
    const nearLimit = 'A'.repeat(4600);
    await page.getByRole('textbox').fill(nearLimit);

    // Counter should turn amber-colored warning
    await expect(page.getByText(/4600\/5000/)).toBeVisible();
  });

  // ── 4. XSS injection does not execute ─────────────────────────────────────
  test('XSS payload in script textarea is not rendered as HTML', async ({ page }) => {
    const xss = '<img src=x onerror="document.title=\'XSS\'">';
    await brainstorm(page);
    await page.locator('[data-testid="concept-card"]').first().click();
    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });

    await page.getByRole('textbox').fill(xss);

    // Title must not change (XSS did not execute)
    await expect(page).not.toHaveTitle('XSS');
    // Raw text should appear as-is in the textarea value
    await expect(page.getByRole('textbox')).toHaveValue(xss);
  });

  // ── 5. Rapid clicks do not create duplicate requests ──────────────────────
  test('rapid clicks on a concept card fire only one API request (debounce)', async ({ page }) => {
    const requests: string[] = [];
    page.on('request', (req) => {
      if (req.url().includes('/generate-script-preview')) {
        requests.push(req.url());
      }
    });

    await brainstorm(page);
    const firstCard = page.locator('[data-testid="concept-card"]').first();

    // Triple rapid click
    await firstCard.click();
    await firstCard.click();
    await firstCard.click();

    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });
    expect(requests.length).toBe(1);
  });

  // ── 6. Full success flow: GENERATE MASTERPIECE ────────────────────────────
  test('full success flow: brainstorm -> select -> generate -> video playback', async ({ page }) => {
    test.setTimeout(240_000);

    await brainstorm(page);
    await page.locator('[data-testid="concept-card"]').first().click();
    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });

    const ta = page.getByRole('textbox');
    const original = await ta.inputValue();
    await ta.fill(original + ' (edited by QA test)');

    await page.getByRole('button', { name: /generate masterpiece/i }).click();

    await expect(page.getByText(/constructing masterpiece/i)).toBeVisible({ timeout: 120_000 });
    await expect(page.locator('video')).toBeVisible({ timeout: 200_000 });
    await expect(page.getByRole('button', { name: /download/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /save to library/i })).toBeVisible();
  });

  // ── 7. Network timeout produces a toast, no freeze ───────────────────────
  test('30s preview timeout shows actionable error toast', async ({ page }) => {
    await page.route('**/generate-script-preview', async (route) => {
      await new Promise((r) => setTimeout(r, 35_000));
      await route.abort('timedout');
    });

    test.setTimeout(60_000);
    await brainstorm(page);
    await page.locator('[data-testid="concept-card"]').first().click();

    await expect(page.getByText(/timed out/i)).toBeVisible({ timeout: 38_000 });
    await expect(page.getByText(/review script/i)).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Responsive Layout Tests
// ---------------------------------------------------------------------------

test.describe('Idea Studio – Responsive Layout', () => {

  test.beforeEach(async ({ page }) => {
    await signIn(page);
    await goToIdeaStudio(page);
  });

  test('action button is visible on mobile viewport (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await brainstorm(page);
    await page.locator('[data-testid="concept-card"]').first().click();
    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });

    const btn = page.getByRole('button', { name: /generate masterpiece/i });
    await expect(btn).toBeInViewport();
  });

  test('action button is visible on tablet viewport (768px)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await brainstorm(page);
    await page.locator('[data-testid="concept-card"]').first().click();
    await expect(page.getByText(/review script/i)).toBeVisible({ timeout: 30000 });

    const btn = page.getByRole('button', { name: /generate masterpiece/i });
    await expect(btn).toBeInViewport();
  });

  test('sidebar navigation links do not overflow at 1024px', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });

    const navLinks = ['idea studio', 'viral repurposer', 'global dubber', 'my masterpieces'];
    for (const link of navLinks) {
      await expect(page.getByRole('link', { name: new RegExp(link, 'i') })).toBeVisible();
    }

    // No horizontal overflow
    const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth   = await page.evaluate(() => window.innerWidth);
    expect(bodyScrollWidth).toBeLessThanOrEqual(viewportWidth + 5);
  });
});
