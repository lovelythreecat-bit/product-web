import { expect, test } from '@playwright/test'
import { resolve } from 'node:path'
import { selectOption } from './ui-controls'

test('two image models save through a drawer with hidden bindings, blank keys and conflict recovery',async({page},info)=>{
  const errors:string[]=[],writes:Record<string,unknown>[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  const connection={id:'c',kind:'image',base_url:'https://agent.example',revision:2,
    has_service_key:true,has_management_key:false,default_config_id:'a',image_model:'fast'}
  let models={revision:2,versions:{'/api/v1/agent-configs/a':1},
    text_model:{base_url:'https://text.example/v1',model:'TEST_ONLY 视觉文字模型',protocol:'chat_completions',has_api_key:true,enabled:true},
    image_model:{base_url:'https://image.example/v1',model:'TEST_ONLY 图片模型',protocol:'openai_images',has_api_key:true,enabled:true}}
  let conflict=false
  await page.route('**/api/v1/admin/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname
    if(path.endsWith('/image/connection'))return route.fulfill({json:connection})
    if(path.endsWith('/image/models')){
      if(request.method()==='PATCH'){
        writes.push(request.postDataJSON())
        if(conflict)return route.fulfill({status:409,json:{code:'CONFLICT',message:'配置已更新'}})
        const body=request.postDataJSON()
        models={...models,revision:3,text_model:{...models.text_model,...body.text_model},
          image_model:{...models.image_model,...body.image_model}}
      }
      return route.fulfill({json:models})
    }
    if(path.endsWith('/text-model-configs'))return route.fulfill({json:{items:[],next_cursor:null}})
    if(path.endsWith('/text-default-model'))return route.fulfill({json:{model_config_id:null,revision:0,connection_revision:0}})
    return route.fulfill({json:path.endsWith('/text-service-connection')?{base_url:null,has_service_key:false,revision:0}:[]})
  })
  await page.goto('/tests/fixtures/agent-configs.html')
  await page.getByRole('button',{name:'图片',exact:true}).click()
  await expect(page.getByRole('heading',{name:'图片模型配置',exact:true})).toBeVisible()
  await expect(page.getByText('文字模型',{exact:true})).toBeVisible()
  await expect(page.getByText('图片生成模型',{exact:true})).toBeVisible()
  for(const label of ['服务配置','模型配置','Agent 方案'])await expect(page.getByRole('button',{name:label,exact:true})).toHaveCount(0)
  const configure=page.getByRole('button',{name:'配置模型',exact:true})
  await configure.click()
  await expect(page.locator('#image-text-url')).toBeFocused()
  await expect(page.locator('#image-text-key')).toHaveValue('')
  await expect(page.locator('#image-generation-key')).toHaveValue('')
  await page.locator('#image-text-model').fill('TEST_ONLY 更新文字模型')
  await selectOption(page.getByRole('combobox',{name:'调用协议',exact:true}),'openrouter_images')
  await expect(page.locator('#image-generation-key')).toHaveAttribute('required','')
  await page.locator('#image-generation-key').fill('TEST_ONLY_private')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false)
  await page.screenshot({path:resolve('../docs/verification/screenshots/image-model-settings-2026-10-16-drawer-'+info.project.name+'.png'),fullPage:true})
  await page.getByRole('button',{name:'保存模型配置',exact:true}).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByText('图片模型配置已保存。',{exact:true})).toBeVisible()
  expect(writes[0]).toMatchObject({expected_revision:2,expected_versions:models.versions,
    text_model:{model:'TEST_ONLY 更新文字模型'},image_model:{protocol:'openrouter_images',api_key:'TEST_ONLY_private'}})
  expect(writes[0].text_model).not.toHaveProperty('api_key')
  await expect(configure).toBeFocused()
  await page.screenshot({path:resolve('../docs/verification/screenshots/image-model-settings-2026-10-16-summary-'+info.project.name+'.png'),fullPage:true})
  await configure.click()
  await expect(page.locator('#image-generation-key')).toHaveValue('')
  await page.locator('#image-text-model').fill('冲突时保留的草稿')
  conflict=true
  await page.getByRole('button',{name:'保存模型配置',exact:true}).click()
  await expect(page.getByText(/关闭后重新打开编辑/)).toBeVisible()
  await expect(page.locator('#image-text-model')).toHaveValue('冲突时保留的草稿')
  await expect(page.getByRole('button',{name:'保存模型配置',exact:true})).toBeDisabled()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.locator('#image-text-model')).toHaveValue('冲突时保留的草稿')
  await page.getByRole('dialog').getByRole('button',{name:'取消',exact:true}).click()
  await expect(configure).toBeFocused()
  expect(errors).toEqual([])
})
