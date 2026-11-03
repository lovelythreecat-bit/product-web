<script setup lang="ts">
defineProps<{ kind?: string; fromSource: boolean }>()
const formats = [
  { kind: 'copy', label: '文案', path: 'M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h6' },
  { kind: 'image', label: '图片', path: 'M4 4h16v16H4z M4 16l5-5 4 4 3-3 4 4 M8 8h.01' },
  { kind: 'video', label: '视频', path: 'M4 5h16v14H4z M10 9l5 3-5 3z' },
]
</script>

<template>
  <div class="creation-empty">
    <div class="creation-empty-sheet">
      <div class="creation-empty-intro">
        <div class="creation-formats" aria-hidden="true">
          <span v-for="format in formats" :key="format.kind" class="creation-format" :class="{ 'is-current': kind === format.kind }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path :d="format.path" /></svg>
            <span>{{ format.label }}</span>
          </span>
        </div>
        <h3>{{ fromSource ? '新草稿已准备好' : '开始一项新创作' }}</h3>
        <p>{{ fromSource ? '已带入来源商品、素材与创作设置，调整后即可开始新的创作。' : '从商品资料开始，让创作贴合你的商品。生成的文案、图片或视频会展示在这里。' }}</p>
      </div>
      <ol class="creation-empty-steps" aria-label="创作步骤">
        <li><span class="step-number" aria-hidden="true">1</span><div><strong>{{ fromSource ? '检查商品资料' : '准备商品资料' }}</strong><span>{{ fromSource ? '核对已带入的商品信息与参考图片' : '填写商品信息，按需添加参考图片' }}</span></div></li>
        <li><span class="step-number" aria-hidden="true">2</span><div><strong>调整创作设置</strong><span>选择适合的规格，补充本次创作要求</span></div></li>
        <li><span class="step-number" aria-hidden="true">3</span><div><strong>确认费用并生成</strong><span>确认后开始生成，在这里查看任务进展</span></div></li>
      </ol>
      <p v-if="fromSource" class="creation-empty-note">原任务与成果保留，本次将创建独立任务。</p>
    </div>
  </div>
</template>

<style scoped>
.creation-empty { min-height:100%; display:grid; place-items:center; padding:28px 32px 48px; box-sizing:border-box }
.creation-empty-sheet { width:100%; max-width:560px; border:1px solid var(--color-border); border-radius:14px; background:var(--color-panel); overflow:hidden }
.creation-empty-intro { padding:40px 32px 28px; text-align:center }
.creation-formats { display:flex; align-items:center; justify-content:center; gap:14px; margin:0 0 28px; min-height:104px }
.creation-format { width:68px; height:84px; display:grid; align-content:center; justify-items:center; gap:8px; border:1px solid var(--color-border); border-radius:10px; color:var(--color-muted); background:var(--color-background) }
.creation-format svg { width:28px; height:28px }
.creation-format>span { font-size:12px; line-height:1.5 }
.creation-format.is-current { width:84px; height:104px; color:var(--color-primary); background:var(--color-selected); border-color:color-mix(in srgb,var(--color-primary) 35%,var(--color-border)) }
.creation-format.is-current svg { width:34px; height:34px }
.creation-empty-intro h3 { margin:0; color:var(--color-text); font-size:22px; line-height:1.5; font-weight:600; text-wrap:balance }
.creation-empty-intro p { max-width:29em; margin:12px auto 0; color:var(--color-muted); font-size:14px; line-height:1.9; text-wrap:pretty }
.creation-empty-steps { display:grid; gap:20px; list-style:none; margin:0 32px 32px; padding:24px 0 0; border-top:1px solid var(--color-border) }
.creation-empty-steps li { display:flex; align-items:flex-start; gap:14px }
.step-number { flex-shrink:0; display:grid; place-items:center; width:28px; height:28px; border-radius:50%; background:var(--color-selected); color:var(--color-primary); font-size:13px; font-variant-numeric:tabular-nums }
.creation-empty-steps li>div { min-width:0; display:grid; gap:4px }
.creation-empty-steps strong { color:var(--color-text); font-size:14px; line-height:1.7; font-weight:500 }
.creation-empty-steps li>div>span { color:var(--color-muted); font-size:13px; line-height:1.7; overflow-wrap:anywhere }
.creation-empty-note { margin:0; padding:14px 24px; border-top:1px solid var(--color-border); background:var(--color-background); color:var(--color-muted); font-size:12px; line-height:1.8; text-align:center }
@media(max-width:1100px) { .creation-empty { padding:20px 20px 32px } .creation-empty-intro { padding:28px 24px 24px } .creation-empty-steps { margin:0 24px 24px } }
@media(max-width:700px) { .creation-empty { min-height:auto; padding:4px 4px 20px } .creation-empty-intro { padding:28px 20px 24px } .creation-empty-intro h3 { font-size:20px } .creation-empty-steps { margin:0 20px 24px; gap:18px } .creation-formats { margin-bottom:24px } }
</style>
