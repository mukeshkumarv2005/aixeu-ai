import { test, expect } from '@playwright/test';

test.describe('Authentication E2E Flow', () => {
  test('logs in successfully and redirects to dashboard', async ({ page }) => {
    // Mock login endpoint
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'fake-e2e-token',
          user: {
            id: 'user-123',
            email: 'e2e@example.com',
            username: 'e2euser',
            display_name: 'E2E User',
            role: 'user',
            is_active: true,
          },
        }),
      });
    });

    // Mock profile endpoint
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-123',
          email: 'e2e@example.com',
          username: 'e2euser',
          display_name: 'E2E User',
          role: 'user',
          is_active: true,
        }),
      });
    });

    // Mock dashboard stats
    await page.route('**/api/v1/dashboard/stats', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_documents: 5,
          total_conversations: 2,
          total_tasks: 10,
        }),
      });
    });

    // Go to login page with redirect
    await page.goto('/auth/login?redirect=/dashboard');

    // Verify page elements
    await expect(page.locator('h1')).toContainText('Sign in');
    
    // Fill form
    await page.fill('input[id="login"]', 'e2e@example.com');
    await page.fill('input[id="password"]', 'password123');

    // Click Login
    await page.click('button[type="submit"]');

    // Wait for redirect to dashboard
    await page.waitForURL('**/dashboard');
    
    // Verify successful login
    await expect(page).toHaveURL(/.*dashboard/);
  });
});
