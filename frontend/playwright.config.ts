import {defineConfig,devices} from '@playwright/test';

export default defineConfig({
 testDir:'./e2e',fullyParallel:true,retries:1,reporter:'list',
 use:{baseURL:'http://127.0.0.1:3100',trace:'retain-on-failure'},
 webServer:{command:'npm run start -- --hostname 127.0.0.1 --port 3100',url:'http://127.0.0.1:3100',reuseExistingServer:false,timeout:120000},
 projects:[{name:'chromium',use:{...devices['Desktop Chrome']}},{name:'mobile',use:{...devices['iPhone 13'],browserName:'chromium'}}],
});
