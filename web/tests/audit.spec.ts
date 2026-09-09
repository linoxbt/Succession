import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const root = '0x' + 'ab'.repeat(32);
const deployment = {chain_id:84532, listing_contract:'0x'+'12'.repeat(20), payment_token:'0x'+'23'.repeat(20),
  identity_registry:'0x'+'34'.repeat(20), identity_registry_is_mock:true, arbiter:'0x'+'45'.repeat(20)};
const row = {listing:{listing_id:'audit-direct',agent_id:'417',seller:'0x'+'56'.repeat(20),buyer:'0x'+'67'.repeat(20),
  seller_signature:'',hash_commitment:root,price:1000000,currency:'USDC',categories:['preferences'],
  valuation_reference:'',state:'escrowed',escrow_balance:1000000,delivered_hash:'',sealed:false,created_at:'',settled_at:''},
  name:'Audit Agent',agent_identity:'erc8004:84532:417',vertical:'Test fixture',valuation:'',preview:{},
  has_envelope:true,has_metadata:true,demo:false,integrity:{},provenance:{}};

test.beforeEach(async ({page}) => {
  page.on('pageerror', error => console.error('Uncaught browser error:', error.message));
  await page.route('**/api/**',async route => {
    const path=new URL(route.request().url()).pathname;
    if(path.startsWith('/api/walkthrough/')) return route.fulfill({status:404,contentType:'application/json',body:'{"detail":"not started"}'});
    let body: unknown;
    if(path==='/api/marketplace') {
      await new Promise(r=>setTimeout(r,100)); body={listings:[],demo_listings:[],count:0,chain:true};
    } else if(path==='/api/listing/audit-direct') {
      await new Promise(r=>setTimeout(r,300)); body=row;
    } else if(path==='/api/chain') body={mode:'chain',chain_id:84532,deployment};
    else if(path==='/api/overview') body={chain:true,totals:{listings:0},listings:[],demo_listings:[],deployment,capabilities:[],reputation_model:{factors:[],grades:[],does_not_transfer:[]}};
    else body={events:[],count:0,chain:true};
    await route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  });
});

test('a delayed direct listing resolves after marketplace refresh',async ({page}) => {
  await page.goto('/app/listing/audit-direct');
  await expect(page.getByText('Audit Agent',{exact:true})).toBeVisible({timeout:15000});
  await expect(page.getByText('No listing at this address.',{exact:false})).toHaveCount(0);
  await expect(page.getByRole('heading',{name:'Independent evaluation'})).toBeVisible();
  await expect(page.getByText(/buyer cannot collect plaintext/i)).toBeVisible();
  await expect(page.getByRole('button',{name:'Reclaim expired escrow'})).toBeDisabled();
});

test('malformed routing recovers without blanking the application',async ({page}) => {
  const errors: string[]=[]; page.on('pageerror', e=>errors.push(e.message));
  await page.goto('/app/marketplace');
  await page.evaluate(()=>{history.pushState({},'', '/app/listing/%E0%A4%A');dispatchEvent(new PopStateEvent('popstate'));});
  await expect(page.locator('#root')).not.toBeEmpty();
  expect(errors).toEqual([]);
});

test('closed menu cannot receive focus and Escape closes an opened menu',async ({page}) => {
  await page.goto('/app/marketplace');
  await expect(page.locator('#console-menu')).toBeHidden();
  const focused = await page.evaluate(()=>{const b=document.querySelector<HTMLButtonElement>('#console-menu button');b?.focus();return document.activeElement===b;});
  expect(focused).toBe(false);
  await page.locator('[aria-controls="console-menu"]').click();
  await expect(page.locator('#console-menu')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('#console-menu')).toBeHidden();
  await expect(page.locator('[aria-controls="console-menu"]')).toBeFocused();
});

for (const route of ['/', '/app', '/app/marketplace', '/app/sell', '/app/claim', '/app/docs', '/app/walkthrough']) {
  test(`route ${route} renders without an uncaught error`,async ({page}) => {
    const errors: string[]=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(route);await expect(page.locator('#root')).not.toBeEmpty();
    expect(errors).toEqual([]);
  });
}

test('sale amounts use exact units and shell arguments stay literal',async ({page}) => {
  await page.goto('/app/sell');
  const result=await page.evaluate(async()=>{
    const helpers=await import('/src/app/commands.ts');
    return {exact:helpers.usdcMinorUnits('9007199254.740993')?.toString(),
      invalid:helpers.usdcMinorUnits('Infinity'),precision:helpers.usdcMinorUnits('1.0000001'),
      argument:helpers.shellArgument("a'; echo dangerous; '")};
  });
  expect(result.exact).toBe('9007199254740993');expect(result.invalid).toBeNull();expect(result.precision).toBeNull();
  expect(result.argument).toBe(`'a'"'"'; echo dangerous; '"'"''`);
});

test('wallet authorization uses the Python request-signing format', async ({page}) => {
  const vector = JSON.parse(readFileSync(new URL('../../fixtures/request-auth.json', import.meta.url), 'utf8'));
  await page.goto('/app/claim');
  const message = await page.evaluate(async input => {
    const { keyRequestMessage } = await import('/src/chain/requestAuth.ts');
    return keyRequestMessage(input.listing_id, input.chain_id, input.contract, input.timestamp, input.nonce);
  }, vector.inputs);
  expect(message).toBe(vector.message);
});

test('landing renders without loading wallet modules and its closed menu cannot focus', async ({page}) => {
  const walletRequests: string[] = [];
  page.on('request', request => {if (/wagmi|walletconnect|chain\/Wallet/.test(request.url())) walletRequests.push(request.url());});
  await page.goto('/');
  await expect(page.getByRole('button', {name:'Connect in app'})).toBeVisible();
  expect(walletRequests).toEqual([]);
  await expect(page.locator('#landing-menu')).toBeHidden();
  await page.locator('[aria-controls="landing-menu"]').click();
  await page.keyboard.press('Escape');
  await expect(page.locator('#landing-menu')).toBeHidden();
});
