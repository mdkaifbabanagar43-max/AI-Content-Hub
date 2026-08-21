import { test, expect } from '@playwright/test';

test('Brand Kit and Repurposer Flow', async ({ page }) => {
  // 1. Go to Brand Kit
  await page.goto('http://localhost:3000/brandkit');
  
  // Wait for loading to finish (the component says "Loading your brand kit..." initially)
  await expect(page.locator('text="Loading your brand kit..."')).not.toBeVisible({ timeout: 10000 });

  // 2. Change font and watermark
  await page.selectOption('select', 'Impact');
  await page.fill('input[placeholder="e.g. @YourBrand"]', '@ViralTest');

  // 3. Save Changes
  await page.click('button:has-text("Save Changes")');

  // Wait for the success toast
  await expect(page.locator('text="Brand kit saved successfully!"')).toBeVisible({ timeout: 5000 });

  // 4. Go to Repurposer
  await page.goto('http://localhost:3000/repurposer');
  await expect(page.locator('text="Viral Repurposer"')).toBeVisible();

  // 5. Submit a YouTube link
  await page.fill('input[placeholder*="youtube.com"]', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
  await page.click('button:has-text("Generate Viral Shorts")');

  // 6. Check for success toast or some UI indicator of processing
  await expect(page.locator('text="Video generation started!"')).toBeVisible({ timeout: 5000 });
});
