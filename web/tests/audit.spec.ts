import { test, expect } from "@playwright/test";

const deployment = {
  listing_contract: "0x642dFC05C9DCC0617c67B318C78dd5AE94134603",
  identity_registry: `0x${"34".repeat(20)}`,
  payment_token: `0x${"23".repeat(20)}`,
  evaluator: `0x${"45".repeat(20)}`,
};

test.beforeEach(async ({ page }) => {
  page.on("pageerror", (error) => console.error("Uncaught browser error:", error.message));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/health"
      ? { status: "ok" }
      : { mode: "chain", chain_id: 84532, head_block: 46600000, explanation: "Verified on Base Sepolia.", deployment };
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

test("dashboard reports the deployment without wallet controls or listing rows", async ({ page }) => {
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Succession is ready to verify." })).toBeVisible();
  await expect(page.getByText("Healthy", { exact: true })).toBeVisible();
  await expect(page.getByText("Base Sepolia", { exact: true })).toBeVisible();
  await expect(page.getByText("3 blocks", { exact: true })).toBeVisible();
  await expect(page.getByText("0x642dFC…134603", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /connect/i })).toHaveCount(0);
  await expect(page.getByText(/marketplace/i)).toHaveCount(0);
});

test("guide exposes the role-separated command sequence", async ({ page }) => {
  await page.goto("/app/guide");
  await expect(page.getByRole("heading", { name: "Use Succession from the terminal." })).toBeVisible();
  await expect(page.getByText("Prepare the seller store")).toBeVisible();
  await expect(page.getByText("Evaluate independently")).toBeVisible();
  await expect(page.getByText("Claim and verify on the buyer host")).toBeVisible();
});

test("terminal checklist contains repeatable recovery commands", async ({ page }) => {
  await page.goto("/app/terminal");
  await expect(page.getByRole("heading", { name: "What to test while recording." })).toBeVisible();
  await expect(page.getByText(/succession fulfil --listing listing-YOUR_ID --once/)).toBeVisible();
  await expect(page.getByText(/succession audit --check-chain/)).toBeVisible();
});

test("closed menu cannot receive focus and Escape closes it", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator("#console-menu")).toBeHidden();
  await page.locator('[aria-controls="console-menu"]').click();
  await expect(page.locator("#console-menu")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#console-menu")).toBeHidden();
  await expect(page.locator('[aria-controls="console-menu"]')).toBeFocused();
});

test("landing opens the dashboard and contains no connect action", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Open dashboard" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: /connect/i })).toHaveCount(0);
});
