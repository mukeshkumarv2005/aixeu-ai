import { test, expect } from '@playwright/test';

test.describe('Storage and Documents E2E Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock refresh endpoint
    await page.route('**/api/v1/auth/refresh', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'fake-e2e-token',
          user: { id: 'user-1', email: 'e2e@example.com' },
        }),
      });
    });

    // Mock profile endpoint
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-1',
          email: 'e2e@example.com',
          username: 'e2euser',
        }),
      });
    });
  });

  test('displays file storage lists', async ({ page }) => {
    // Mock files endpoint
    await page.route('**/api/v1/storage/files', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          files: [
            {
              id: 'file-1',
              filename: 'report.pdf',
              mime_type: 'application/pdf',
              size_bytes: 10240,
              storage_path: 'uploads/report.pdf',
              is_processed: true,
              processed_at: '2026-07-04T12:00:00Z',
              created_at: '2026-07-04T12:00:00Z',
              is_temporary: false,
              updated_at: null,
            },
            {
              id: 'file-2',
              filename: 'notes.txt',
              mime_type: 'text/plain',
              size_bytes: 512,
              storage_path: 'uploads/notes.txt',
              is_processed: false,
              processed_at: null,
              created_at: '2026-07-04T12:10:00Z',
              is_temporary: false,
              updated_at: null,
            },
          ],
          total: 2,
        }),
      });
    });

    // Go to storage page
    await page.goto('/storage');

    // Verify files listed
    await expect(page.locator('text=report.pdf')).toBeVisible();
    await expect(page.locator('text=notes.txt')).toBeVisible();
  });
});
