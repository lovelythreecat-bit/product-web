import { expect, test } from '@playwright/test'

test('dialog keyboard isolation, cancel-first, rapid reopen, drawer scroll and focus restore',async({page},info)=>{
 await page.goto('/tests/fixtures/overlays.html')
 const charge=page.getByRole('button',{name:'打开收费确认'})
 await charge.click()
 const modal=page.getByRole('dialog',{name:'确认本次费用'})
 await expect(modal.getByRole('button',{name:'取消'})).toBeFocused()
 for(let i=0;i<8;i++){await page.keyboard.press('Tab');expect(await modal.evaluate(el=>el.contains(document.activeElement))).toBe(true)}
 for(let i=0;i<8;i++){await page.keyboard.press('Shift+Tab');expect(await modal.evaluate(el=>el.contains(document.activeElement))).toBe(true)}
 await page.keyboard.press('Escape');await expect(charge).toBeFocused()
 for(let i=0;i<5;i++){await charge.click();await page.keyboard.press('Escape');await charge.click();await expect(modal).toBeVisible();await expect(modal.getByRole('button',{name:'取消'})).toBeFocused();await page.keyboard.press('Escape')}
 await page.getByRole('button',{name:'删除确认',exact:true}).click()
 await expect(page.getByRole('dialog',{name:'删除作品'}).getByRole('button',{name:'取消'})).toBeFocused()
 await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'删除确认',exact:true})).toBeFocused()
 await page.getByRole('button',{name:'编辑资料',exact:true}).click()
 await expect(page.getByLabel('商品名称')).toBeFocused()
 await page.keyboard.press('Escape')
 await page.getByRole('button',{name:'预览',exact:true}).click()
 await expect(page.getByRole('heading',{name:'作品预览'})).toBeFocused()
 await expect(page.getByRole('dialog').getByRole('button',{name:'取消'})).toHaveCount(0)
 await page.keyboard.press('Escape')
 await page.getByRole('button',{name:'打开详情'}).click()
 const drawer=page.getByRole('dialog',{name:'任务详情'})
 await expect(drawer.getByRole('heading')).toBeFocused()
 const rect=await drawer.boundingBox()
 if(info.project.name==='mobile'){expect(rect?.width).toBe(390);expect(rect?.height).toBe(844)}
 const headerBefore=await drawer.locator('header').boundingBox()
 await drawer.locator('.overlay-content').evaluate(el=>el.scrollTop=el.scrollHeight)
 expect(await drawer.locator('header').boundingBox()).toEqual(headerBefore)
 await page.screenshot({path:info.outputPath('drawer.png')})
 await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'打开详情'})).toBeFocused()
})

test('six routes keep authenticated navigation and responsive V2 layout',async({page},info)=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
 for(const path of ['/login','/register']) {
  await page.goto(path)
  await expect(page.getByLabel('账号',{exact:true})).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 }
 await page.getByLabel('账号',{exact:true}).fill('TEST_ONLY_nav_'+crypto.randomUUID().slice(0,8))
 await page.getByLabel('密码',{exact:true}).fill('TEST_ONLY_navigation_password')
 await page.getByRole('button',{name:'创建账号',exact:true}).click()
 await expect(page).toHaveURL(/\/workspace$/)
 for(const path of ['/workspace','/workspace/TEST_ONLY','/works','/account','/recharge']){
  await page.goto(path)
  if(path.startsWith('/workspace')||path==='/works') await expect(page.getByRole('heading',{name:'业务页面正在开发'})).toBeVisible()
  else await expect(page.getByRole('heading',{name:path==='/account'?'个人中心':'充值说明',exact:true})).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 }
 await page.goto('/workspace')
 await page.screenshot({path:info.outputPath('shell.png'),fullPage:true})
 await page.getByRole('button',{name:'开发说明'}).click()
 await expect(page.getByRole('dialog',{name:'开发说明'})).toBeVisible()
 await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'开发说明'})).toBeFocused()
 await page.getByRole('link',{name:'充值积分'}).click();await expect(page).toHaveURL(/\/recharge$/)
 expect(errors).toEqual([])
})
