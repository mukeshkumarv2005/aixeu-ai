import { test, expect } from '@playwright/test';

test.describe('Chat E2E Flow', () => {
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

  test('displays conversation list and loads messages', async ({ page }) => {
    // Mock conversations endpoint
    await page.route('**/api/v1/chat/conversations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          conversations: [
            { id: 'conv-1', title: 'First Conversation', model: 'gpt-4o', is_archived: false, created_at: '2026-07-04T12:00:00Z', message_count: 2 },
            { id: 'conv-2', title: 'Second Conversation', model: 'gpt-4o', is_archived: false, created_at: '2026-07-04T12:05:00Z', message_count: 0 },
          ],
          total: 2,
        }),
      });
    });

    // Mock messages endpoint for conv-1
    await page.route('**/api/v1/chat/conversations/conv-1/messages', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          messages: [
            { id: 'msg-1', conversation_id: 'conv-1', role: 'user', content: 'Hello AI', created_at: '2026-07-04T12:01:00Z' },
            { id: 'msg-2', conversation_id: 'conv-1', role: 'assistant', content: 'Hello! How can I help you today?', created_at: '2026-07-04T12:01:05Z' },
          ],
          total: 2,
        }),
      });
    });

    // Go to chat page
    await page.goto('/chat');

    // Verify first conversation title is visible in sidebar
    await expect(page.locator('text=First Conversation')).toBeVisible();
    await expect(page.locator('text=Second Conversation')).toBeVisible();

    // Click on the first conversation
    await page.click('text=First Conversation');

    // Verify conversation messages are loaded and rendered
    await expect(page.locator('text=Hello AI')).toBeVisible();
    await expect(page.locator('text=Hello! How can I help you today?')).toBeVisible();
  });
});
