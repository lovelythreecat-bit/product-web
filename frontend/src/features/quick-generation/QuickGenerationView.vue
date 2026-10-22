<script setup lang="ts">
import { MAX_PRODUCT_REFERENCES } from '../workspace/materialLimits'
import { computed, onScopeDispose, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { ElCheckbox } from 'element-plus/es/components/checkbox/index'
import { ElRadio } from 'element-plus/es/components/radio/index'
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import AppDialog from '../../components/AppDialog.vue'
import TaskCard from '../../components/TaskCard.vue'
import QuickImageHistory from './QuickImageHistory.vue'
import QuickCopyHistory from './QuickCopyHistory.vue'
import QuickCopyRequirements from './QuickCopyRequirements.vue'
import QuickProductEditor from './QuickProductEditor.vue'
import QuickProductSummary from './QuickProductSummary.vue'
import { platforms, outputs, useQuickGeneration } from './useQuickGeneration'
import './quick-generation.css'
const { run, draft, product, agents, step, progressStep, readOnly, canGoToStep, goToStep, kind, current, currentItems, copyEntries, multipleCopies, copyReady, updateCopy, complete, stageStatus, locked, loading, busy, error, feedback, conflict, requirementsOpen, chargeOpen, uncertain, pendingBatch, total, imageCount, estimated, imageQuotes, estimateBusy, requiredFields, materials, frameCandidates, framesLoading, framesError, readFrames, uploadControl, uploading, refresh, initialize, prepare, submit, closeCharge, advance, saveExit, savedProduct, upload, removeMaterial, copy, fileContentUrl } = useQuickGeneration()
const names = ['商品确认', '营销文案', '图片生成', '视频生成']
const productEditor = ref<InstanceType<typeof QuickProductEditor>>()
const blocked = computed(() => readOnly.value || busy.value || uploading.value || locked.value || uncertain.value || conflict.value)
const navigationBlocked = computed(() => busy.value || productEditor.value?.busy || uploading.value || uncertain.value || conflict.value || chargeOpen.value)
async function persistProduct(required = false) {
  if (readOnly.value || step.value !== 1 || !productEditor.value) return true
  if (!productEditor.value.dirty && (!required || product.value)) return true
  return productEditor.value.save()
}
async function openCopyRequirements() {
  if (await persistProduct(true)) copyRequirementsOpen.value = true
}
async function goToSavedStep(target: number) {
  if (target === step.value || await persistProduct()) await goToStep(target)
}
async function saveProductAndExit() {
  if (await persistProduct()) await saveExit()
}
async function saveEditedProductBeforeLeaving() {
  if (productEditor.value?.busy) return false
  if (productEditor.value?.dirty) return persistProduct()
}
onBeforeRouteLeave(saveEditedProductBeforeLeaving)
onBeforeRouteUpdate(saveEditedProductBeforeLeaving)
function warnUnsavedProduct(event: BeforeUnloadEvent) { if (productEditor.value?.dirty) event.preventDefault() }
window.addEventListener('beforeunload', warnUnsavedProduct)
onScopeDispose(() => window.removeEventListener('beforeunload', warnUnsavedProduct))
const navigationOnly = computed(() => {
  if (readOnly.value) return step.value < 5
  const next = step.value === 1 ? 'copy' : step.value === 2 ? 'image' : step.value === 3 ? 'video' : null
  if (!next || !currentItems(next).some(item => item.task_id)) return false
  const saved = run.value?.state.draft
  if (step.value === 2 && saved && (draft.value.copy_text !== saved.copy_text || JSON.stringify(draft.value.copy_texts) !== JSON.stringify(saved.copy_texts || {}))) return false
  if (step.value === 3 && saved && (draft.value.image_platform !== saved.image_platform || JSON.stringify(draft.value.image_outputs) !== JSON.stringify(saved.image_outputs))) return false
  return true
})
const copyRequirementsOpen = ref(false)
const originalsOpen = ref(false)
let previousCopyRequirements: { types: string[]; parameters: Record<string, string | number | boolean> } | null = null
watch(copyRequirementsOpen, open => {
  if (open) previousCopyRequirements = { types: [...draft.value.copy_types], parameters: { ...draft.value.copy_parameters } }
}, { flush: 'sync' })
watch(() => run.value?.run_id, () => { copyRequirementsOpen.value = false; originalsOpen.value = false })
function changeRequirements(types: string[], parameters: Record<string, string | number | boolean>) {
  if (readOnly.value || chargeOpen.value) return
  if (JSON.stringify(draft.value.copy_types) !== JSON.stringify(types)) draft.value.copy_types = types
  if (JSON.stringify(draft.value.copy_parameters) !== JSON.stringify(parameters)) draft.value.copy_parameters = parameters
}
async function confirmRequirements(types: string[], parameters: Record<string, string | number | boolean>) {
  if (readOnly.value) return
  if (chargeOpen.value) { await submit(); if (!chargeOpen.value && !error.value) copyRequirementsOpen.value = false; return }
  changeRequirements(types, parameters)
  const shownCredits = estimated.value
  await prepare('copy')
  if (chargeOpen.value && shownCredits !== null && total.value === shownCredits) {
    await submit(); if (!chargeOpen.value && !error.value) copyRequirementsOpen.value = false
  }
}
const estimateTotal = computed(() => estimated.value)
function selectOutput(value: typeof outputs[number]['value'], checked: unknown) { draft.value.image_outputs = checked ? [...draft.value.image_outputs.filter(v => v !== value), value] : draft.value.image_outputs.filter(v => v !== value) }
function regenerationHint(used = 0) { return used < 3 ? '免费重新生成剩余 ' + (3 - used) + ' 次' : '免费次数已用完，再次生成将计费' }
async function confirmCopy() {
  await advance('confirm_copy')
  if (!error.value && progressStep.value === 3) requirementsOpen.value = true
}
async function confirmImageSelection() {
  if (chargeOpen.value) { await submit(); if (!chargeOpen.value && !error.value) requirementsOpen.value = false; return }
  const shownCredits = estimated.value
  await prepare('image')
  if (chargeOpen.value && shownCredits !== null && total.value === shownCredits) {
    await submit(); if (!chargeOpen.value && !error.value) requirementsOpen.value = false
  }
}
async function closeRequirements(target: 'copy' | 'image', open: boolean) {
  if (busy.value) return
  const prepared = chargeOpen.value
  if (!open && chargeOpen.value) await closeCharge(false)
  if (target === 'copy') {
    if (!open && !prepared && !uncertain.value && previousCopyRequirements) {
      draft.value.copy_types = previousCopyRequirements.types
      draft.value.copy_parameters = previousCopyRequirements.parameters
    }
    copyRequirementsOpen.value = open
  }
  else requirementsOpen.value = open
}
async function uploadDroppedFiles(files: File[]) {
  if (blocked.value) return
  if (files.some(file => !['image/png', 'image/jpeg', 'image/webp'].includes(file.type))) { error.value = '请上传 PNG、JPG 或 WebP 图片。'; return }
  if (files.length + materials.value.length > MAX_PRODUCT_REFERENCES) { error.value = `最多上传 ${MAX_PRODUCT_REFERENCES} 张图片，还可以添加 ${Math.max(0, MAX_PRODUCT_REFERENCES - materials.value.length)} 张。`; return }
  for (const file of files) { if (blocked.value || !await upload(file)) break }
}
async function uploadSelectedFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  await uploadDroppedFiles(files)
}
function regenerateItem(target: 'copy' | 'image', index: number) {
  const item = currentItems(target)[index]
  if (target === 'image' && item?.detail?.task.state === 'FAILED' && item.detail.task.settlement_state === 'RELEASED') {
    const output = outputs.find(output => output.value === item.request.input.parameters.output_type)
    if (output) void prepare('image', [output.value])
    return
  }
  void prepare(target, undefined, index)
}
</script>
<template>
  <section class="quick-root">
    <header class="quick-page-heading" aria-label="快速生成"><div class="quick-title-line"><h1>快速生成</h1><span class="quick-page-caption">{{ readOnly ? "已完成 · 只读查看" : "从商品到文案、图片与视频" }}</span></div><UiButton v-if="run" class="button quick-exit" type="button" :disabled="busy || productEditor?.busy || uploading || conflict" @click="saveProductAndExit">{{ readOnly ? '返回作品' : '保存并退出' }}</UiButton></header>
    <p v-if="loading" role="status">正在读取快速生成进度…</p>
    <template v-else-if="run">
      <div v-if="error || uncertain || feedback" class="quick-notice"><p v-if="error" class="field-error" role="alert">{{ error }}</p><p v-if="feedback" role="status">{{ feedback }}</p><template v-if="uncertain && pendingBatch"><p>本次费用请求已保存。请核对原批次后继续，不会另建收费请求。</p><UiButton type="button" class="button" :disabled="busy" @click="chargeOpen = true">核对原批次费用</UiButton></template><UiButton v-if="conflict" type="button" class="button" @click="refresh(true)">重新读取进度（放弃本页未保存修改）</UiButton><UiButton v-else-if="error" type="button" class="button" :disabled="busy" @click="refresh()">刷新进度</UiButton></div>
      <div class="quick-wizard">
        <ol class="quick-stepper" aria-label="快速生成步骤"><li v-for="(name, index) in names" :key="name" :class="{ current: step === index + 1, done: progressStep > index + 1 }"><button type="button" :disabled="navigationBlocked || !canGoToStep(index + 1)" :aria-current="step === index + 1 ? 'step' : undefined" @click="goToSavedStep(index + 1)"><span class="quick-step-number"><svg v-if="progressStep > index + 1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg><template v-else>{{ index + 1 }}</template></span><span><strong>{{ name }}</strong></span></button></li></ol>
        <div class="quick-body"><div class="quick-content" :class="{ 'quick-canvas': step > 1, 'quick-product-content': step === 1 }"><header class="quick-stage-heading"><div><h2>{{ step < 5 ? names[step - 1] : "本次创作已完成" }}</h2><span>{{ readOnly ? "成果只读查看" : step === 1 ? "确认商品信息与参考图片" : step === 2 ? "确认文案后继续图片创作" : step === 3 ? "预览完整成果" : step === 4 ? "确认方案后继续出片" : "文案、图片与视频" }}</span></div></header>
          <p v-if="stageStatus && !complete" class="quick-stage-status" role="status" aria-live="polite">{{ stageStatus }}</p>
          <template v-if="step === 1">
            <QuickProductSummary :read-only="readOnly" :product="product" :materials="materials" :disabled="blocked" :uploading="uploading" @upload="uploadControl?.click()" @remove="removeMaterial" @drop-files="uploadDroppedFiles"><template v-if="!readOnly" #editor><QuickProductEditor ref="productEditor" inline :open="true" :owner-key="run.run_id" :product="product" :required-fields="requiredFields" :disabled="blocked" :persist="savedProduct"/></template></QuickProductSummary>
            <input v-if="!readOnly" ref="uploadControl" hidden type="file" multiple accept="image/png,image/jpeg,image/webp" aria-label="上传商品图片" :disabled="blocked || materials.length >= MAX_PRODUCT_REFERENCES" @change="uploadSelectedFiles"/>
          </template>
          <template v-else-if="step === 2">
            <div class="quick-copy-grid">
              <template v-if="multipleCopies"><div v-for="(entry, index) in copyEntries" :key="entry.key" class="quick-copy-paper"><label :for="'quick-copy-' + index">{{ entry.label }} <small>{{ readOnly ? '只读' : complete ? '可编辑' : '生成完成后可编辑' }}</small></label><UiInput :id="'quick-copy-' + index" :model-value="draft.copy_texts[entry.key] || ''" :aria-label="entry.label" type="textarea" :rows="8" maxlength="100000" :readonly="readOnly" :disabled="!readOnly && (blocked || !complete)" placeholder="正在生成文案，完整保存后显示在这里…" @update:model-value="updateCopy(entry.key, String($event))"/><div class="quick-copy-footer"><small v-if="readOnly">已确认</small><template v-else><div class="quick-regeneration"><UiButton type="button" class="button text-button" :disabled="blocked || !complete" @click="regenerateItem('copy', index)">重新生成</UiButton><small>{{ regenerationHint(entry.free_regenerations_used) }}</small></div></template><QuickCopyHistory v-if="currentItems('copy')[index]" :run="run" :item="currentItems('copy')[index]!" :agents="agents"/><UiButton type="button" class="button text-button" :disabled="!draft.copy_texts[entry.key]" @click="copy(draft.copy_texts[entry.key])">复制</UiButton></div></div></template>
              <div v-else class="quick-copy-paper"><label for="quick-copy-text">{{ copyEntries[0]?.label || '营销文案' }} <small>{{ readOnly ? '只读' : complete ? '可编辑' : '生成完成后可编辑' }}</small></label><UiInput id="quick-copy-text" v-model="draft.copy_text" aria-label="营销文案" type="textarea" :rows="13" maxlength="100000" :readonly="readOnly" :disabled="!readOnly && (blocked || !complete)" :placeholder="current.length ? '正在生成文案，完整保存后显示在这里…' : '请返回商品确认，先生成营销文案。'"/><div class="quick-copy-footer"><small v-if="readOnly">已确认文案，仅供查看和复制</small><template v-else-if="current.length"><div class="quick-regeneration"><UiButton type="button" class="button text-button" :disabled="blocked || !complete" @click="regenerateItem('copy', 0)">重新生成</UiButton><small>{{ regenerationHint(copyEntries[0]?.free_regenerations_used) }}</small></div></template><QuickCopyHistory v-if="currentItems('copy')[0]" :run="run" :item="currentItems('copy')[0]!" :agents="agents"/><UiButton type="button" class="button text-button" :disabled="!draft.copy_text" @click="copy()">复制文案</UiButton></div></div>
            </div>
            <div v-if="!readOnly" class="action-row"><UiButton class="button" type="button" :disabled="blocked" @click="copyRequirementsOpen = true">{{ current.length ? '重新选择文案类型' : '生成文案' }}</UiButton><UiButton class="button text-button" type="button" :disabled="blocked" @click="copyRequirementsOpen = true">调整创作要求</UiButton></div>
            <div v-if="current.length" class="quick-originals">
              <UiButton type="button" class="button text-button quick-originals-toggle" :aria-expanded="originalsOpen" aria-controls="quick-original-tasks" @click="originalsOpen = !originalsOpen">{{ originalsOpen ? '收起原始任务' : '查看原始任务' }}</UiButton>
              <div v-if="originalsOpen" id="quick-original-tasks">
                <section v-for="item in current" :key="item.detail?.task.task_id || item.task_id || item.label" class="quick-original"><TaskCard :compact-label="item.label" :allow-plan-revision="true" quick-generation :read-only="readOnly" :regeneration-disabled="blocked" v-if="item.detail" :key="item.detail.task.task_id" :detail="item.detail" :agent="agents.find(a => a.agent_id === item.detail!.agent_id)" @media-changed="refresh()" @regenerate="regenerateItem('copy', current.indexOf(item))"/></section>
              </div>
            </div>
          </template>
          <template v-else-if="step === 3"><p v-if="!current.length" class="field-hint">选择图片类型与目标平台，确认费用后开始生成。</p>

            <section v-for="(item, index) in current" :key="item.detail?.task.task_id || item.task_id || item.label" class="quick-image-result">
              <header class="quick-image-heading"><h3>{{ item.label }}</h3><QuickImageHistory :run="run" :item="item" :agents="agents" /></header>
              <TaskCard :allow-plan-revision="true" quick-generation :read-only="readOnly" :regeneration-disabled="blocked" v-if="item.detail" :key="item.detail.task.task_id" :detail="item.detail" :agent="agents.find(a => a.agent_id === item.detail!.agent_id)" @media-changed="refresh()" @regenerate="regenerateItem('image', index)"/><UiButton v-if="!readOnly && item.detail?.task.state === 'FAILED' && item.detail.task.settlement_state === 'RELEASED'" type="button" class="button" :disabled="blocked" @click="regenerateItem('image', index)">重新生成此项</UiButton><p v-if="!readOnly" class="field-hint">{{ regenerationHint(item.free_regenerations_used) }}<span v-if="item.request?.input?.parameters?.output_type === 'detail_page'">；此项为完整的 3 张详情图。</span></p>
            </section>

          </template>
          <template v-else-if="step === 4">
            <fieldset v-if="!current.length" :disabled="blocked" class="quick-video-settings"><fieldset class="first-frame-choice"><legend>视频首帧 <small>必选</small></legend><p class="field-hint">从商品参考图或本次已确认的生成图片中选择。</p><p v-if="framesLoading" role="status">正在读取生成图片…</p><p v-if="framesError" class="field-error" role="alert">{{ framesError }} <UiButton type="button" class="button text-button" @click="readFrames">重新读取图片</UiButton></p><p v-if="!frameCandidates.length && !framesLoading" class="field-hint">上传商品图片或确认本次图片成果后即可选择。</p><ElRadio v-for="frame in frameCandidates" :key="frame.file_id" v-model="draft.video_first_frame_file_id" class="frame-option" name="quick-first-frame" :value="frame.file_id" :disabled="blocked"><img :src="fileContentUrl(frame.file_id)" :alt="frame.label"/><span>{{ frame.label }}</span></ElRadio></fieldset></fieldset>
            <TaskCard :allow-plan-revision="true" quick-generation :read-only="readOnly" :regeneration-disabled="blocked" v-for="item in current" v-show="item.detail" :key="item.detail?.task.task_id || item.task_id || item.label" :detail="item.detail!" :agent="agents.find(a => a.agent_id === item.detail?.agent_id)" @media-changed="refresh()" @regenerate="prepare('video')"/>
            <UiButton v-if="current.length && !locked && !readOnly" type="button" class="button" :disabled="blocked" @click="prepare('video')">重新确认费用生成视频</UiButton>
          </template>
          <template v-else>
            <section v-for="type in (['copy', 'image', 'video'] as const)" :key="type" class="quick-completed-section">
              <h3>{{ type === 'copy' ? '已确认营销文案' : type === 'image' ? '图片成果' : '视频成果' }}</h3>
              <template v-if="type === 'copy'"><div class="action-row"><QuickCopyHistory v-for="item in currentItems('copy')" :key="item.task_id || item.label" :run="run" :item="item" :agents="agents" show-label/></div><pre class="quick-confirmed-copy">{{ run.state.confirmed_copy }}</pre></template>
              <template v-else>
                <section v-for="item in currentItems(type)" v-show="item.detail" :key="item.detail?.task.task_id || item.task_id || item.label" :class="{ 'quick-completed-image': type === 'image' }">
                  <header v-if="type === 'image'" class="quick-image-heading"><h4>{{ item.label }}</h4><QuickImageHistory :run="run" :item="item" :agents="agents" /></header>
                  <TaskCard :allow-plan-revision="true" quick-generation :read-only="readOnly" :regeneration-disabled="blocked" :detail="item.detail!" :agent="agents.find(a => a.agent_id === item.detail?.agent_id)" @media-changed="refresh()" @regenerate="prepare(type)"/>
                </section>
              </template>
            </section>
          </template>
        </div>
</div>
        <footer class="quick-footer">
          <div><p v-if="error" class="field-error quick-footer-error" role="alert">{{ error }}</p>
            <div v-if="step !== 1 && !navigationOnly && !readOnly" class="quick-footer-hint">
              <template v-if="step === 1 || step === 3 && !current.length || step === 4 && !current.length"><span>{{ step === 1 ? '下一步：生成营销文案' : step === 3 ? '已选 ' + draft.image_outputs.length + ' 类 · ' + imageCount + ' 张' : '本次视频' }}</span><strong v-if="estimateTotal !== null"> {{ estimateTotal }} <small>积分</small></strong><small v-if="estimateBusy">正在读取费用…</small></template>
              <template v-else><span>{{ locked ? '任务执行中' : readOnly ? '已完成 · 只读查看' : '' }}</span></template>
            </div>
          </div>
          <div class="quick-footer-actions">
            <UiButton v-if="step > 1 && step < 5" class="button text-button" type="button" :disabled="navigationBlocked" @click="advance('back')">上一步</UiButton>
            <UiButton v-if="navigationOnly" class="button primary" type="button" :disabled="navigationBlocked" @click="goToSavedStep(step + 1)">{{ step === 4 ? '查看汇总' : '下一步' }}</UiButton>
            <UiButton v-else-if="step === 1" class="button primary" type="button" :disabled="blocked || productEditor?.busy" @click="openCopyRequirements">确认商品，生成文案</UiButton>
            <UiButton v-else-if="step === 2" class="button primary" type="button" :disabled="blocked || !complete || !copyReady" @click="confirmCopy">确认文案，生成图片</UiButton>
            <UiButton v-else-if="step === 3 && !current.length" class="button primary" type="button" :disabled="blocked" @click="requirementsOpen = true">确认费用并生成图片</UiButton>
            <UiButton v-else-if="step === 3" class="button primary" type="button" :disabled="blocked || !complete" @click="advance('confirm_images')">确认图片，继续视频</UiButton>
            <UiButton v-else-if="step === 4 && !current.length" class="button primary" type="button" :disabled="blocked" @click="prepare('video')">确认费用，生成视频方案</UiButton>
            <UiButton v-else-if="step === 4" class="button primary" type="button" :disabled="blocked || !complete" @click="advance('finish')">完成并汇总成果</UiButton>
            <RouterLink v-else class="button primary" to="/works">完成并查看作品</RouterLink>
          </div>
        </footer>
      </div>
    </template>
    <div v-else-if="error" class="quick-notice"><p class="field-error" role="alert">{{ error }}</p><UiButton type="button" class="button" @click="initialize">重新读取</UiButton></div>
    <p v-else role="status">正在打开创作页面…</p>
    <QuickCopyRequirements v-if="!readOnly" :open="copyRequirementsOpen" :types="draft.copy_types" :parameters="draft.copy_parameters" :busy="busy" :error="error" :credits="chargeOpen ? total : estimated" :prepared="chargeOpen" :uncertain="uncertain" @update:open="closeRequirements('copy', $event)" @change="changeRequirements" @confirm="confirmRequirements"/>
    <AppDialog :open="requirementsOpen && !readOnly" @update:open="closeRequirements('image', $event)" title="选择图片内容" purpose="charge">
            <fieldset :disabled="blocked || chargeOpen" class="quick-image-settings"><div class="quick-platform"><label for="quick-image-platform">目标平台 <small>必选</small></label><UiSelect id="quick-image-platform" v-model="draft.image_platform" aria-label="目标平台" required><option value="" disabled>请选择目标平台</option><option v-for="[value, label] in platforms" :key="value" :value="value">{{ label }}</option></UiSelect></div>
              <div class="quick-output-options"><ElCheckbox v-for="output in outputs" :key="output.value" class="quick-output-option" :class="{ selected: draft.image_outputs.includes(output.value) }" :model-value="draft.image_outputs.includes(output.value)" :disabled="blocked || chargeOpen" @change="selectOutput(output.value, $event)"><span class="quick-output-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path v-if="output.value === 'main_image'" d="M3 3h18v18H3z M3 17l5-6 5 5 3-4 5 5 M8 7h.01"/><path v-else-if="output.value === 'detail_page'" d="m12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5"/><path v-else d="M7 2h10v20H7z M7 9h10 M7 16h10"/></svg></span><span class="quick-output-description"><strong>{{ output.label }}</strong><small>{{ output.description }}</small></span><span class="quick-output-price">{{ output.count }} 张<small>{{ imageQuotes[output.value] === undefined ? '' : imageQuotes[output.value] + ' 积分' }}</small></span></ElCheckbox></div>
              </fieldset>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      <p class="quick-charge-total" aria-live="polite"><span>使用</span><strong>{{ chargeOpen ? total : estimated === null ? '—' : estimated }} <small>积分</small></strong></p>
      <template #actions><UiButton class="button primary" type="button" :disabled="blocked" @click="confirmImageSelection">{{ busy ? '正在提交…' : uncertain ? '核对原批次' : '确认生成图片' }}</UiButton></template>
    </AppDialog>
    <AppDialog :open="chargeOpen && !copyRequirementsOpen && !requirementsOpen && !readOnly" @update:open="closeCharge" title="确认生成" purpose="charge"><p class="quick-charge-total"><span>使用</span><strong>{{ total }} <small>积分</small></strong></p><p v-if="error" class="field-error" role="alert">{{ error }}</p><template #actions><UiButton class="button primary" type="button" :disabled="busy || !pendingBatch" @click="submit">{{ busy ? '正在提交…' : uncertain ? '核对原批次' : '确认生成' }}</UiButton></template></AppDialog>
  </section>
</template>
