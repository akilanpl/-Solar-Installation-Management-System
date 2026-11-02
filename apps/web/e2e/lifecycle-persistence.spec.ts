/** Real saved-record checks; run after the isolated lifecycle campaign. No backend mocks. */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";
const credentials = () => JSON.parse(readFileSync(resolve(process.cwd(), "../../var/completion-customer.json"), "utf8")) as {identifier:string;password:string};
async function login(page:Page){const user=credentials();await page.goto('/login');await page.getByLabel('Email',{exact:true}).fill(user.identifier);await page.getByLabel('Password',{exact:true}).fill(user.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page).toHaveURL(/\/customer$/);}

test('product coverage remains visible on My equipment after customer relogin',async({page})=>{
 await login(page);
 const orders=await page.request.get('/api/v1/orders?page_size=100');expect(orders.status()).toBe(200);
 const units=[] as {serial_number:string;status:string}[];
 for(const order of (await orders.json()).items){const response=await page.request.get(`/api/v1/orders/${order.id}/unit-warranties`);expect(response.status()).toBe(200);units.push(...await response.json());}
 expect(units.length,'Campaign must have legitimately activated saved coverage').toBeGreaterThan(0);
 await page.getByRole('link',{name:'My equipment',exact:true}).click();
 const section=page.getByRole('region',{name:'Order-bound product warranties'});
 for(const unit of units)await expect(section.getByText(unit.serial_number,{exact:false})).toBeVisible();
 await expect(page.getByRole('heading',{name:'No equipment',exact:true})).toHaveCount(0);
 await page.reload();for(const unit of units)await expect(section.getByText(unit.serial_number,{exact:false})).toBeVisible();
});

test('payment receipts retain simulation provenance and customer cannot access staff roster',async({page})=>{
 await login(page);await page.getByRole('link',{name:'Payments',exact:true}).click();
 await expect(page.getByText('Test-only record; no money moved',{exact:false})).toBeVisible();
 expect((await page.request.get('/api/v1/admin/employees')).status()).toBe(403);
 const provider=await page.request.get('/api/v1/payments/razorpay/capability');expect(provider.status()).toBe(200);expect((await provider.json()).mode).toBe('test');
});

// Focused frontend contract regression. Only the job read/create response is
// controlled; this is separate from the real persisted business acceptance.
test('new installation job appears in calendar without reloading (frontend contract regression)',async({page})=>{
 const {previewAccount}=await import('./preview-accounts');const user=previewAccount('sales');
 await page.goto('/login');await page.getByLabel('I am signing in as').selectOption('sales');await page.getByLabel('Employee ID',{exact:true}).fill(user.identifier);await page.getByLabel('Password',{exact:true}).fill(user.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page).toHaveURL(/\/sales$/);
 let job:Record<string,unknown>|null=null;
 await page.route('**/api/v1/jobs',async route=>{
  if(route.request().method()==='POST'){const body=route.request().postDataJSON();job={...body,id:'10000000-0000-4000-8000-000000000099',reference:'JOB-UI-REGRESSION',status:'created',slot_starts_at:null,otp_verified:false};await route.fulfill({status:201,json:job});}
  else await route.fulfill({json:job?[job]:[]});
 });
 await page.goto('/sales/installations');
 await expect(page.getByRole('combobox',{name:'Work record',exact:true}).locator('option').filter({hasText:'JOB-UI-REGRESSION'})).toHaveCount(0);
 await page.getByRole('combobox',{name:'Active technician',exact:true}).selectOption({label:'Kavya Rao · EMP-TECH-001'});
 await page.getByRole('button',{name:'Create assigned job',exact:true}).click();
 await expect(page.getByRole('combobox',{name:'Work record',exact:true}).locator('option').filter({hasText:'JOB-UI-REGRESSION'})).toHaveCount(1);
});
