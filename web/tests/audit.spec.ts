import { test, expect } from "@playwright/test";

const deployment = { listing_contract: "0x642dFC05C9DCC0617c67B318C78dd5AE94134603", identity_registry: `0x${"34".repeat(20)}`, payment_token: `0x${"23".repeat(20)}`, arbiter: "0x518477058d12e60D74E42b799F5ad0f5c4FFf31b" };

test.beforeEach(async ({ page }) => {
  page.on("pageerror", error => console.error("Uncaught browser error:", error.message));
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/health" ? { status: "ok" } : { mode: "chain", chain_id: 84532, head_block: 46600000, deployment };
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
  });
});

for (const route of ["/", "/app", "/app/guide", "/app/terminal", "/app/docs", "/app/marketplace"]) {
  test(`${route} renders without an uncaught error`, async ({ page }) => {
    const errors: string[] = []; page.on("pageerror", error => errors.push(error.message)); await page.goto(route);
    await expect(page.locator("#root")).not.toBeEmpty(); expect(errors).toEqual([]);
  });
}

test("landing uses the ShelbyHost visual structure", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("the property layer for agent memory")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Transfer memory with verifiable ownership." })).toBeVisible();
  await expect(page.getByText("7/7")).toBeVisible();
  await expect(page.getByText("Portable memory packages")).toBeVisible();
  await expect(page.getByRole("button", { name: /connect|buy/i })).toHaveCount(0);
  expect(await page.locator(":root").evaluate(el => getComputedStyle(el).getPropertyValue("--primary").trim())).toBe("oklch(0.72 0.18 347)");
});

test("dashboard uses the ShelbyHost sidebar and card arrangement", async ({ page }) => {
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Protocol operations." })).toBeVisible();
  await expect(page.getByText("Healthy", { exact: true })).toBeVisible();
  await expect(page.getByText("Base Sepolia", { exact: true })).toBeVisible();
  await expect(page.getByText("3 blocks", { exact: true })).toBeVisible();
  await expect(page.getByText("Base Sepolia contracts")).toBeVisible();
  await expect(page.getByText("Three parties, one atomic handover")).toBeVisible();
  await expect(page.getByText(/marketplace/i)).toHaveCount(0);
});

test("guide and video checklist expose copyable commands", async ({ page }) => {
  await page.goto("/app/guide"); await expect(page.getByRole("heading", { name: "Run Succession from your terminal." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy to clipboard" }).first()).toBeVisible();
  await page.goto("/app/terminal"); await expect(page.getByRole("heading", { name: "Test Succession while you record." })).toBeVisible();
  await expect(page.getByText(/succession audit --check-chain/)).toBeVisible();
});

test("mobile dashboard uses the ShelbyHost sticky navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/app");
  const mobileNav = page.getByRole("navigation").last(); await expect(mobileNav).toBeVisible();
  await mobileNav.getByRole("button", { name: "Guide" }).click();
  await expect(page.getByRole("heading", { name: "Run Succession from your terminal." })).toBeVisible();
});
