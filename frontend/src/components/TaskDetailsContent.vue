<script setup lang="ts">
import { computed } from 'vue'
import type { Schema } from '../types/api'
import { fileContentUrl } from '../api/files'
import { fieldLabel, labeledEntries } from '../features/workspace/display'

const props = defineProps<{
  detail: Schema<'TaskDetail'>
  agent?: Schema<'AgentVersion'>
  stateLabel: string
  settlementLabel: string
  createdAt?: string
}>()
const products = computed(() => labeledEntries(props.detail.input.product, 'product').map(entry => ({ ...entry, value: typeof props.detail.input.product[entry.key] === 'object' ? readableValue(props.detail.input.product[entry.key], 'product') : entry.value })))
const materials = computed(() => props.detail.input.material_versions || [])
const valueLabels: Record<string, Record<string, string>> = {
  platform: { amazon: 'Amazon', taobao: '淘宝', tmall: '天猫', jd: '京东', pinduoduo: '拼多多', shopee: 'Shopee', lazada: 'Lazada', shein: 'SHEIN', temu: 'Temu' },
  output_type: { main_image: '商品主图', detail_page: '详情图（3 张）', pdd_white_background: '白底图', long_image: '商品长图' },
}
function readableValue(value: unknown, category: 'product' | 'parameter'): string {
  if (Array.isArray(value)) return value.map(item => readableValue(item, category)).join('、')
  if (value && typeof value === 'object') return Object.entries(value).map(([key, item], index) => `${fieldLabel(key, category, index)}：${readableValue(item, category)}`).join('\n')
  if (typeof value === 'boolean') return value ? '开启' : '关闭'
  return value === null || value === undefined || value === '' ? '未填写' : String(value)
}
const parameters = computed(() => Object.entries(props.detail.input.parameters || {})
  .filter(([, value]) => value !== '' && value !== null && value !== undefined)
  .map(([key, value], index) => ({ key, label: fieldLabel(key, 'parameter', index), value: key === 'first_frame_file_id'
    ? `商品参考图 ${materials.value.findIndex(material => material.file_id === value) + 1 || '（历史素材）'}`
    : valueLabels[key]?.[String(value)] || readableValue(value, 'parameter') })))
</script>
<template>
  <div class="task-details-content">
    <section class="detail-overview" aria-label="任务概览">
      <div class="overview-heading"><h3>{{ agent?.kind === 'image' ? '图片创作' : agent?.kind === 'video' ? '视频创作' : agent?.kind === 'copy' ? '文案创作' : agent?.name || '创作任务' }}</h3><span class="detail-state">{{ stateLabel }}</span></div>
      <p class="detail-task-number">{{ detail.task.display_number || '编号待更新' }}</p>
      <div class="detail-cost"><span>本次费用 <strong>{{ detail.task.quote.credits }}</strong> 积分</span><span>{{ settlementLabel }}</span></div>
      <dl class="overview-metadata"><dt v-if="createdAt">生成时间</dt><dd v-if="createdAt"><time :datetime="detail.task.created_at">{{ createdAt }}</time></dd><dt>会话编号</dt><dd>{{ detail.conversation_display_number || '编号待更新' }}</dd><dt v-if="agent?.name">生成服务</dt><dd v-if="agent?.name">{{ agent.name }}</dd></dl>
    </section>
    <section class="detail-section" aria-label="生成输入">
      <h3>生成输入</h3><h4>创作指令</h4>
      <p class="detail-instruction">{{ detail.input.instruction || '按商品资料生成' }}</p>
      <h4>商品资料</h4>
      <dl v-if="products.length" class="snapshot-fields"><div v-for="entry in products" :key="entry.key"><dt>{{ entry.label }}</dt><dd>{{ entry.value }}</dd></div></dl>
      <p v-else class="detail-empty">本次未填写商品资料</p>
      <template v-if="materials.length"><h4>参考素材 <span>{{ materials.length }} 张</span></h4><div class="detail-materials"><figure v-for="(material, index) in materials" :key="material.file_id"><img :src="fileContentUrl(material.file_id)" :alt="'提交时的商品参考图 ' + (index + 1)" loading="lazy" /><figcaption>商品参考图 {{ index + 1 }}<span v-if="material.file_id === detail.input.parameters?.first_frame_file_id">视频首帧</span></figcaption></figure></div></template>
    </section>
    <section class="detail-section" aria-label="生成设置"><h3>生成设置</h3><dl v-if="parameters.length" class="snapshot-fields"><div v-for="entry in parameters" :key="entry.key"><dt>{{ entry.label }}</dt><dd>{{ entry.value }}</dd></div></dl><p v-else class="detail-empty">本次未单独指定生成设置</p></section>
  </div>
</template>
<style scoped>
.task-details-content { color:var(--color-text); font-size:14px; line-height:1.7; min-width:0 }
.detail-overview { padding:18px; background:var(--color-background); border-radius:12px }
.overview-heading { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px }
.overview-heading h3 { margin:0; font-size:18px; font-weight:600 }
.detail-state { color:var(--color-primary); font-size:12px; font-weight:600 }
.detail-task-number { margin:4px 0 16px; color:var(--color-muted); font-size:12px; font-variant-numeric:tabular-nums; overflow-wrap:anywhere }
.detail-cost { display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:4px 12px; padding-bottom:14px; border-bottom:1px solid var(--color-border); font-size:13px }
.detail-cost strong { margin:0 3px; font-size:20px; font-weight:600; font-variant-numeric:tabular-nums }
.detail-cost>span:last-child { color:var(--color-muted); font-size:12px }
.overview-metadata { display:grid; grid-template-columns:auto minmax(0,1fr); gap:7px 18px; margin:14px 0 0; font-size:12px }
.overview-metadata dt { color:var(--color-muted) }
.overview-metadata dd { margin:0; overflow-wrap:anywhere; text-align:right; font-variant-numeric:tabular-nums }
.detail-section { margin-top:28px }
.detail-section+.detail-section { padding-top:22px; border-top:1px solid var(--color-border) }
.detail-section h3 { margin:0 0 16px; font-size:16px; font-weight:600 }
.detail-section h4 { display:flex; align-items:baseline; gap:8px; margin:22px 0 10px; font-size:13px; font-weight:600 }
.detail-section h3+h4 { margin-top:0 }
.detail-section h4>span { color:var(--color-muted); font-size:12px; font-weight:400 }
.detail-instruction { margin:0; padding:14px 16px; background:var(--color-background); border-radius:8px; white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.9 }
.snapshot-fields { margin:0 }
.snapshot-fields>div { display:grid; grid-template-columns:90px minmax(0,1fr); align-items:start; gap:12px; padding:10px 0; border-bottom:1px solid var(--color-border) }
.snapshot-fields>div:first-child { padding-top:0 }
.snapshot-fields>div:last-child { border-bottom:0; padding-bottom:0 }
.snapshot-fields dt { color:var(--color-muted); font-size:13px }
.snapshot-fields dd { margin:0; min-width:0; white-space:pre-wrap; overflow-wrap:anywhere }
.detail-empty { margin:0; color:var(--color-muted); font-size:13px }
.detail-materials { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px }
.detail-materials figure { margin:0; min-width:0 }
.detail-materials img { display:block; width:100%; aspect-ratio:1; object-fit:contain; background:var(--color-background); border:1px solid var(--color-border); border-radius:8px }
.detail-materials figcaption { margin-top:6px; font-size:12px; color:var(--color-muted); text-align:center }
.detail-materials figcaption span { display:block; color:var(--color-primary) }
@media(max-width:480px) { .detail-overview { padding:16px } .snapshot-fields>div { grid-template-columns:78px minmax(0,1fr); gap:10px } .detail-materials { grid-template-columns:repeat(2,minmax(0,1fr)) } }
</style>
