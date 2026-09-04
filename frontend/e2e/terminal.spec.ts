import {expect,test} from '@playwright/test';

test.beforeEach(async({page})=>{
 await page.route('**/api/v1/**',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:{message:'offline test'}})}));
 await page.goto('/');
});

test('terminal shell is keyboard accessible',async({page})=>{
 await expect(page.getByText('NEXUS')).toBeVisible();
 await page.getByRole('button',{name:/Sembol veya şirket ara/}).click();
 await expect(page.getByPlaceholder('Sembol, şirket veya kripto ara')).toBeFocused();
 await page.keyboard.press('Escape');
 await expect(page.getByPlaceholder('Sembol, şirket veya kripto ara')).toBeHidden();
});

test('paper ticket exposes every simulated order type',async({page})=>{
 const select=page.getByLabel('Emir türü');
 await expect(select.locator('option')).toHaveCount(6);
 await select.selectOption('stop_limit');
 await expect(page.getByText('Limit fiyatı')).toBeVisible();
 await expect(page.getByText('Stop fiyatı')).toBeVisible();
});

test('mobile keeps primary navigation usable',async({page},testInfo)=>{
 test.skip(testInfo.project.name!=='mobile');
 await expect(page.getByText('Terminal',{exact:true})).toBeVisible();
 await expect(page.getByText('Portföy',{exact:true})).toBeVisible();
});

test('locale switch translates primary navigation',async({page})=>{
 await page.getByRole('button',{name:/Ayarlar/}).click();
 await page.getByRole('button',{name:'English'}).click();
 await expect(page.getByText('Markets',{exact:true})).toBeVisible();
});

test('synchronized multi-chart workspace is reachable',async({page})=>{
 await page.goto('/multichart');
 await expect(page.getByRole('heading',{name:'Senkronize Çoklu Grafik'})).toBeVisible();
 await expect(page.getByRole('combobox')).toHaveValue('15m');
});
