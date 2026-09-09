import { test, expect } from "@playwright/test";

const deployment = {
  listing_contract: "0x642dFC05C9DCC0617c67B318C78dd5AE94134603",
  identity_registry: `0x${"34".repeat(20)}`,
  payment_token: `0x${"23".repeat(20)}`,
  arbiter: `0x${"45".repeat(20)}`,
};

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  page.on("pageerror", (error) => console.error("Uncaught browser error:", error.message));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/health" ? { status: "ok" }
      : { mode: "chain", chain_id: 84532, head_block: 46600000, deployment };
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
  });
});

for (const route of ["/", "/app", "/app/guide", "/app/terminal", "/app/docs", "/app/marketplace"]) {
  test(`${route} renders without an uncaught error`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(route);
    await expect(page.locator("#root")).not.toBeEmpty();
    expect(errors).toEqual([]);
  });
}

test("landing matches the Triacta page structure", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(14, 13, 11)");
  await expect(page.getByText("SUCCESSION", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "The code is replaceable. The memory is not." })).toBeVisible();
  await expect(page.getByText("Three checks, one atomic handover.")).toBeVisible();
  await expect(page.getByRole("button", { name: /connect/i })).toHaveCount(0);
});

test("dashboard mirrors the Triacta sidebar, cards, and table arrangement", async ({ page }) => {
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "What Succession is connected to" })).toBeVisible();
  await expect(page.getByText("Healthy", { exact: true })).toBeVisible();
  await expect(page.getByText("Base Sepolia", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("3 blocks", { exact: true })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Component" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Collapse sidebar" })).toBeVisible();
  await expect(page.getByText(/marketplace/i)).toHaveCount(0);
});

test("sidebar collapses and preserves the preference", async ({ page }) => {
  await page.goto("/app");
  await page.getByRole("button", { name: "Collapse sidebar" }).click();
  await expect(page.getByRole("button", { name: "Expand sidebar" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("button", { name: "Expand sidebar" })).toBeVisible();
});

test("theme toggle uses the Triacta light palette", async ({ page }) => {
  await page.goto("/app");
  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(245, 241, 232)");
});

test("guide and runbook expose copyable terminal steps", async ({ page }) => {
  await page.goto("/app/guide");
  await expect(page.getByRole("heading", { name: "Run Succession from your terminal." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy to clipboard" }).first()).toBeVisible();
  await page.goto("/app/terminal");
  await expect(page.getByRole("heading", { name: "Test Succession while you record." })).toBeVisible();
  await expect(page.getByText(/succession audit --check-chain/)).toBeVisible();
});

test("mobile dashboard uses the Triacta off-canvas navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/app");
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(page.getByRole("dialog", { name: "Mobile navigation" })).toBeVisible();
  await page.getByRole("button", { name: /Succession Guide/ }).click();
  await expect(page.getByRole("heading", { name: "Run Succession from your terminal." })).toBeVisible();
});
