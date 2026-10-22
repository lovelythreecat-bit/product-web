import { expect, test } from '@playwright/test'
import { resolve } from 'node:path'
import { selectOption } from './ui-controls'

test('video models, sound and runtime settings use real upstream parameters',async({page},info)=>{
  const errors:string[]=[],writes:{path:string;body:Record<string,unknown>}[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  const profile={profile_id:'00000000-0000-4000-8000-000000000002',version:3,adapter:'wan',
    base_url:'https://wan.example/api/v1',model:'wan2.2-i2v-flash',enabled:true,has_api_key:true,max_segment_seconds:5}
  const models={revision:2,configuration_revision:4,models:{planner:null,video:profile,visual:null},bindings:{}}
  const resolutions={'9:16':[1080,1920],'16:9':[1920,1080],'1:1':[1080,1080],'4:5':[1080,1350],
    '3:4':[1080,1440],'4:3':[1440,1080],'3:2':[1620,1080],'2:3':[1080,1620]}
  const settings={configuration_revision:4,mode:'fake',duration_tiers:[5,10,15,30],default_duration:10,
    max_images:12,max_file_bytes:20971520,video_bitrate:8000000,audio_bitrate:192000,lease_seconds:60,resolutions}
  await page.route('**/api/v1/admin/**',async route=>{
    const path=new URL(route.request().url()).pathname
    if(route.request().method()==='PATCH')writes.push({path,body:route.request().postDataJSON()})
    if(path.endsWith('/connection'))return route.fulfill({json:{id:'c1',kind:'video',revision:2,base_url:'https://video.example',has_service_key:true,has_management_key:true}})
    if(path.includes('/video/models'))return route.fulfill({json:models})
    if(path.endsWith('/video/audio'))return route.fulfill({json:{revision:2,enabled:false}})
    if(path.endsWith('/settings'))return route.fulfill({json:settings})
    if(path.endsWith('/text-model-configs'))return route.fulfill({json:{items:[],next_cursor:null}})
    if(path.endsWith('/text-default-model'))return route.fulfill({json:{model_config_id:null,revision:0,connection_revision:0}})
    if(path.endsWith('/text-service-connection'))return route.fulfill({json:{base_url:null,has_service_key:false,revision:0,updated_at:null}})
    return route.fulfill({json:[]})
  })
  await page.goto('/tests/fixtures/agent-configs.html')
  await page.getByRole('button',{name:'视频',exact:true}).click()
  await expect(page.getByRole('heading',{name:'视频模型配置',exact:true})).toBeVisible()
  await expect(page.getByRole('heading',{name:'分镜文本模型',exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'角色绑定'})).toHaveCount(0)
  await page.screenshot({path:resolve('../docs/verification/screenshots/video-agent-configs-2026-10-17-'+info.project.name+'.png'),fullPage:true})
  const action=page.locator('[data-configure-video]')
  await action.click()
  await expect(page.getByRole('combobox',{name:'视频供应商',exact:true})).toBeFocused()
  await expect(page.getByLabel('替换 API Key（留空保留）',{exact:true})).toHaveValue('')
  await page.getByLabel('单段最长秒数',{exact:true}).fill('10')
  await page.screenshot({path:resolve('../docs/verification/screenshots/video-agent-drawer-2026-10-17-'+info.project.name+'.png'),fullPage:true})
  await page.getByRole('button',{name:'保存模型配置',exact:true}).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  expect(writes[0]?.body).toMatchObject({expected_revision:2,expected_configuration_revision:4,
    expected_profile_id:profile.profile_id,expected_profile_version:3,adapter:'wan',max_segment_seconds:10})
  expect(writes[0]?.body).not.toHaveProperty('api_key')
  await action.click()
  await selectOption(page.getByRole('combobox',{name:'视频供应商',exact:true}),'seedance')
  await expect(page.getByLabel('单段最长秒数',{exact:true})).toHaveCount(0)
  await expect(page.getByLabel('API Key',{exact:true})).toHaveAttribute('required','')
  await page.getByLabel('API Key',{exact:true}).fill('TEST_ONLY_not_saved')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByLabel('API Key',{exact:true})).toHaveValue('TEST_ONLY_not_saved')
  await page.getByRole('dialog').getByRole('button',{name:'取消',exact:true}).click()
  await expect(action).toBeFocused()
  await action.click()
  await expect(page.getByLabel('替换 API Key（留空保留）',{exact:true})).toHaveValue('')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByRole('dialog').getByRole('button',{name:'取消',exact:true}).click()
  await page.getByRole('button',{name:'运行设置',exact:true}).click()
  await expect(page.getByRole('combobox',{name:'出片方式',exact:true})).toBeFocused()
  await expect(page.getByText('非敏感参数（JSON 对象）',{exact:true})).toHaveCount(0)
  await page.getByRole('button',{name:'保存运行设置',exact:true}).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  expect(writes[1]?.body).toMatchObject({expected_connection_revision:2,config:{expected_version:4,duration_tiers:[5,10,15,30],resolutions}})
  await page.getByRole('button',{name:'声音设置',exact:true}).click()
  await selectOption(page.getByRole('combobox',{name:'成片声音',exact:true}),'true')
  await page.getByRole('button',{name:'保存声音设置',exact:true}).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  expect(writes[2]?.body).toEqual({expected_revision:2,expected_configuration_revision:4,enabled:true})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false)
  expect(errors).toEqual([])
})
