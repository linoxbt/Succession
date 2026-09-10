import { test, expect } from "@playwright/test";

const deployment = { listing_contract: "0x642dFC05C9DCC0617c67B318C78dd5AE94134603", identity_registry: "0x7177a6867296406881E20d6647232314736Dd09A", payment_token: "0x036CbD53842c5426634e7929541eC2318f3dCF7e", arbiter: "0x518477058d12e60D74E42b799F5ad0f5c4FFf31b" };

test.beforeEach(async ({ page }) => {
  page.on("pageerror", error => console.error("Uncaught browser error:", error.message));
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/health" ? { status: "ok" } : { mode: "chain", chain_id: 84532, head_block: 46600000, deployment };
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
  });
});

for (const route of ["/", "/app", "/app/guide", "/app/docs", "/app/terminal", "/app/marketplace"]) {
  test(route + " renders without an uncaught error", async ({ page }) => {
    const errors: string[] = []; page.on("pageerror", error => errors.push(error.message)); await page.goto(route);
    await expect(page.locator("#root")).not.toBeEmpty(); expect(errors).toEqual([]);
  });
}

test("original Succession mark is restored and video navigation is removed", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('svg path[stroke="#00C3F7"]').first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Video Script" })).toHaveCount(0);
  await expect(page.getByText("Video Script", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Docs" })).toBeVisible();
});

test("dashboard contains only the requested operational summary", async ({ page }) => {
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Succession dashboard." })).toBeVisible();
  await expect(page.getByText("Healthy", { exact: true })).toBeVisible();
  await expect(page.getByText("Base Sepolia", { exact: true })).toBeVisible();
  await expect(page.getByText("Head block", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Finality policy", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Base Sepolia contracts")).toHaveCount(0);
  await expect(page.getByText("Three parties, one atomic handover")).toHaveCount(0);
  await expect(page.getByText("What the live release proves")).toHaveCount(0);
});

test("guide covers installation, help, first transfer, and recovery", async ({ page }) => {
  await page.goto("/app/guide");
  await expect(page.getByRole("heading", { name: "Install Succession and make your first transfer." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Install the Succession CLI" })).toBeVisible();
  await expect(page.getByText(/pipx install/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Learn the CLI before sending transactions" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Claim into the successor store" })).toBeVisible();
  await expect(page.getByText(/--successor-agent/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Verify, retry, and recover" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy to clipboard" }).first()).toBeVisible();
});

test("docs provides deployment, protocol, CLI, security, and recovery reference", async ({ page }) => {
  await page.goto("/app/docs");
  await expect(page.getByRole("heading", { name: "Succession protocol reference." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Live Base Sepolia deployment" })).toBeVisible();
  await expect(page.getByText(deployment.listing_contract)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Settlement lifecycle" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "CLI command reference" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Security model" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recovery and finality" })).toBeVisible();
});

test("removed terminal route falls back to dashboard and mobile navigation includes docs", async ({ page }) => {
  await page.goto("/app/terminal");
  await expect(page.getByRole("heading", { name: "Succession dashboard." })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/app");
  const nav = page.getByRole("navigation").last();
  await expect(nav.getByRole("button", { name: "Docs" })).toBeVisible();
  await expect(nav.getByText("Video Script", { exact: true })).toHaveCount(0);
});
