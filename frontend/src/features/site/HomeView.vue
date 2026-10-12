<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as api from '../../api/site'
import type { Schema } from '../../types/api'
import { useAdminRequest } from '../admin/shared'
import { session } from '../auth/session'
const content = ref<Schema<'SiteContentView'> | null>(null)
const cases = ref<Schema<'PublicCaseView'>[]>([])
const {busy,error,run} = useAdminRequest()
const capabilities = [{key:'text',label:'文案 Agent'},{key:'image',label:'图片 Agent'},{key:'video',label:'视频 Agent'}] as const
function load() { return run(() => Promise.all([api.getPublicSite(),api.getPublicCases()]), ([site,items]) => {content.value=site.content;cases.value=items}) }
onMounted(load)
</script>
<template>
 <div class="site-home">
  <p v-if="error" class="field-error" role="alert">{{ error }} <button class="button" @click="load">重新读取</button></p>
  <section class="site-intro" aria-labelledby="site-title"><div><p class="site-eyebrow">产品介绍</p><h1 id="site-title">电商 AI 创作平台</h1><p v-if="content?.content" class="site-lead">{{ content.content.product_intro }}</p><p v-else-if="busy" role="status">正在读取产品介绍…</p><p v-else class="site-lead">产品介绍正在准备中，批准后将在这里展示。</p><div class="site-actions"><RouterLink class="button primary" to="/register">注册体验</RouterLink><RouterLink class="button" to="/login">登录</RouterLink><RouterLink v-if="session.profile.value" class="button" to="/workspace">进入工作台</RouterLink></div></div></section>
  <section v-if="content?.content" class="site-section" aria-labelledby="capabilities-title"><h2 id="capabilities-title">三个 Agent</h2><div class="site-capabilities"><article v-for="item in capabilities" :key="item.key"><h3>{{ item.label }}</h3><p>{{ content.content.agent_descriptions[item.key] }}</p></article></div></section>
  <section v-if="content?.content" class="site-section" aria-labelledby="process-title"><h2 id="process-title">使用流程</h2><ol class="site-process"><li v-for="(step,index) in content.content.process_steps" :key="index">{{ step }}</li></ol></section>
  <section class="site-section" aria-labelledby="cases-title"><h2 id="cases-title">真实作品案例</h2><p v-if="!cases.length">暂无已获公开展示授权的真实案例。</p><div v-else class="site-cases"><article v-for="item in cases" :key="item.id" class="panel"><h3>授权作品</h3><template v-for="copy in item.items" :key="copy.id"><img v-if="copy.media_type.startsWith('image/')" :src="copy.url" alt="已获公开展示授权的作品" loading="lazy"><video v-else-if="copy.media_type==='video/mp4'" :src="copy.url" controls preload="none" aria-label="已获授权的视频作品" /><a v-else :href="copy.url" target="_blank" rel="noopener">查看授权文案</a></template></article></div></section>
 </div>
</template>
<style scoped>
.site-home{max-width:1120px;margin:auto;padding:clamp(24px,5vw,64px)}.site-intro{padding:32px 0 56px;max-width:800px}.site-eyebrow{color:var(--color-muted);font-size:14px}.site-intro h1{font-size:clamp(28px,4vw,42px);line-height:1.3}.site-lead{font-size:18px;line-height:1.9;white-space:pre-wrap}.site-actions{display:flex;gap:16px;flex-wrap:wrap;margin-top:32px}.site-section{padding:32px 0;border-top:1px solid var(--color-border);overflow-wrap:anywhere}.site-capabilities{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:32px}.site-capabilities p{line-height:1.8;white-space:pre-wrap}.site-process{display:grid;gap:20px;padding-left:24px;line-height:1.7}.site-cases{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.site-cases img,.site-cases video{display:block;max-width:100%;height:auto;margin-bottom:16px}@media(max-width:700px){.site-capabilities,.site-cases{grid-template-columns:1fr}.site-intro{padding-top:16px}}
</style>
