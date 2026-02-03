import { test, expect } from '@playwright/test'

const LIVE_BASE = 'https://mitchelldawkinsjr.github.io/NBA-Stat-Spot/'

/**
 * E2E test: Verify players data loads on the live GitHub Pages site.
 * Starts at home, navigates to Explore via nav, then Browse Teams → selects a team.
 */
test('players data loads on GitHub Pages', async ({ page }) => {
  // Desktop viewport so nav links (Dashboard, Explore) are visible (they're hidden on mobile)
  await page.setViewportSize({ width: 1280, height: 720 })

  // Start at live home page and wait for app to load
  await page.goto(LIVE_BASE, { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: 'Dashboard', level: 2 })).toBeVisible({ timeout: 25000 })

  // Navigate to Explore via client-side: open sidebar then click Explore (direct /explore can 404 on GitHub Pages)
  await page.getByRole('button', { name: 'Toggle menu' }).click()
  await page.getByRole('link', { name: 'Explore' }).click()
  await expect(page.getByRole('heading', { name: /Explore Players & Teams/i })).toBeVisible({ timeout: 15000 })

  // Switch to "Browse Teams" so we load teams and then team players
  await page.getByRole('button', { name: /Browse Teams/i }).click()

  // Wait for teams to load: NBA Teams heading and at least one team button
  await expect(page.getByRole('heading', { name: /NBA Teams/i })).toBeVisible({ timeout: 20000 })
  const teamsList = page.locator('div.space-y-2').filter({ has: page.locator('button') })
  await expect(teamsList.locator('button').first()).toBeVisible({ timeout: 20000 })

  // Click first team to load players
  await teamsList.locator('button').first().click()

  // Wait for players section to finish loading (Loading players... disappears)
  await expect(page.getByText('Loading players...')).toHaveCount(0, { timeout: 25000 })

  // We should see either "X players found" with player links, or "No players found"
  const playersFound = page.getByText(/\d+ player(s)? found/i)
  const noPlayers = page.getByText('No players found for this team')
  const playerLinks = page.locator('a[href*="/player/"]')

  const sawCount = await playersFound.isVisible().catch(() => false)
  const sawNone = await noPlayers.isVisible().catch(() => false)
  const sawLinks = (await playerLinks.count()) > 0

  expect(sawCount || sawNone || sawLinks, 'Expected either players count, "No players found", or player profile links').toBe(true)
  if (sawCount) {
    await expect(playerLinks.first()).toBeVisible({ timeout: 5000 })
  }
})
