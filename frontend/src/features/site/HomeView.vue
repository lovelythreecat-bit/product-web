<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import UiButton from '../../components/ui/UiButton.vue'
import * as api from '../../api/site'
import type { Schema } from '../../types/api'
import { useAdminRequest } from '../admin/shared'
import { session } from '../auth/session'
import CreativeIcon from './components/CreativeIcon.vue'
import BrandMark from '../../components/BrandMark.vue'
import UserMenu from '../../components/UserMenu.vue'
import ThemeToggle from '../../components/ThemeToggle.vue'
import { brandName } from './brand'
import './homepage.css'

const cases = ref<Schema<'PublicCaseView'>[]>([])
const { busy, error, run } = useAdminRequest()
const capabilities = [
  { key: 'text', label: '文案创作', title: '把亮点，写到心动处。', kind: '商品文案', sampleTitle: '把轻盈，穿进日常。', copy: '从出门的第一步，到城市的每一段路。清爽的色调，简单的搭配，让日常穿着多一点自在。', meta: '从商品资料出发，让卖点更有画面感。' },
  { key: 'image', label: '图片创作', title: '给商品，一个亮眼的画面。', kind: '图片创作', sampleTitle: '给商品，一个亮眼的画面。', copy: '结合商品资料、参考图片与创作要求，探索商品主图、详情图和商品长图的不同表达。', meta: '创作类型与费用以实际配置为准。' },
  { key: 'video', label: '视频创作', title: '让商品故事，动起来。', kind: '视频创作', sampleTitle: '让商品故事，动起来。', copy: '以商品介绍和图片为起点，准备视频创作要求，确认方案后开始生成。', meta: '此处展示能力说明，不是已生成的视频。' },
] as const
const activeCapability = ref(0)
const selectedCapability = computed(() => capabilities[activeCapability.value]!)
const categories = [
  { key: 'fashion', label: '鞋服', caption: '让风格先被看见。', alt: '运动鞋与卫衣展示示例' },
  { key: 'beauty', label: '美妆', caption: '细节里的美，值得被看见。', alt: '美妆瓶罐展示示例' },
  { key: 'digital', label: '数码', caption: '换个角度，呈现科技的质感。', alt: '耳机展示示例' },
] as const
const steps = [
  { title: '带上商品素材', description: '准备商品图片、名称与卖点。' },
  { title: '选个创作方向', description: '选择文案、图片或视频，填写创作要求。' },
  { title: '看清费用再开始', description: '提交前确认本次创作内容与费用。' },
  { title: '收下你的新作品', description: '到我的作品查看、预览与下载。' },
]
// The approved showcase is identical in development and production. Real cases
// continue to come exclusively from the authorized public-content API.
function load() {
  return run(() => Promise.all([api.getPublicSite(), api.getPublicCases()]), ([, items]) => {
    cases.value = items
  })
}
async function navigateCapability(event: KeyboardEvent, index: number) {
  let next = index
  if (event.key === 'ArrowDown' || event.key === 'ArrowRight') next = (index + 1) % capabilities.length
  else if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') next = (index + capabilities.length - 1) % capabilities.length
  else if (event.key === 'Home') next = 0
  else if (event.key === 'End') next = capabilities.length - 1
  else return
  event.preventDefault()
  const tablist = (event.currentTarget as HTMLElement).parentElement
  activeCapability.value = next
  await nextTick()
  tablist?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus()
}
onMounted(load)
</script>

<template>
  <div id="home-top" class="site-home">
    <header class="home-header home-wrap">
      <a class="home-brand" href="#home-top" :aria-label="brandName + '，返回顶部'"><BrandMark class="home-brand-mark" /><span class="home-brand-copy"><span class="brand-name" :title="brandName">{{ brandName }}</span><small>电商 AI 创作平台</small></span></a>
      <nav class="home-nav" aria-label="首页导航"><a href="#capabilities">创作能力</a><a href="#scenarios">应用场景</a><a href="#how-it-works">工作方式</a></nav>
      <div class="home-account-links"><ThemeToggle /><template v-if="session.profile.value"><RouterLink class="home-button home-button--compact home-workspace-link" to="/workspace" target="_blank" rel="noopener noreferrer">进入工作台</RouterLink><UserMenu /></template><template v-else><RouterLink class="home-button home-button--secondary home-button--compact home-login" to="/login">登录</RouterLink><RouterLink class="home-button home-button--compact" to="/register">注册体验</RouterLink></template></div>
    </header>
    <div class="home-main">
      <section class="home-hero home-wrap" aria-labelledby="site-title">
        <div class="home-hero-copy"><h1 id="site-title">让好商品，<br><em>亮眼登场。</em></h1><p class="home-hero-lead">从一句打动人心的文案，到一张吸睛的主图、<br class="desktop-break">一支有看点的视频。让每一次创作，都围绕你的商品。</p><div class="home-hero-actions"><RouterLink class="home-button" to="/workspace" target="_blank" rel="noopener noreferrer">探索创作工作台<CreativeIcon class="home-diagonal-arrow" type="arrow" /></RouterLink><a class="home-text-link" href="#capabilities">看看能做什么<span aria-hidden="true">↓</span></a></div><div class="home-capability-line"><span v-for="item in capabilities" :key="item.key">{{ item.label }}</span></div></div>
        <figure class="home-hero-stage"><img class="home-hero-art" :src="'/homepage/commerce-hero-v3.png'" alt="鞋服、美妆和数码商品的创作示例" width="1536" height="1024" fetchpriority="high"><figcaption><span>商品有亮点，表达有新意。</span><span>创作示例</span></figcaption></figure>
      </section>
      <section id="capabilities" class="home-capabilities home-wrap" aria-labelledby="capabilities-title">
        <div class="home-section-intro"><h2 id="capabilities-title">一个商品，<br>不止一种精彩。</h2><p>把商品信息变成适合不同场景的内容。<br>你决定创作方向，{{ brandName }}陪你把想法展开。</p></div>
        <div class="home-capability-layout"><div class="home-capability-nav" role="tablist" aria-label="创作能力"><button v-for="(item, index) in capabilities" :id="'home-tab-' + item.key" :key="item.key" type="button" role="tab" :aria-selected="activeCapability === index" aria-controls="home-capability-panel" :tabindex="activeCapability === index ? 0 : -1" @click="activeCapability = index" @keydown="navigateCapability($event, index)"><span class="home-tab-title">{{ item.label }}<CreativeIcon class="home-diagonal-arrow" type="arrow" /></span><span>{{ item.title }}</span></button></div><div id="home-capability-panel" class="home-capability-panel" role="tabpanel" :aria-labelledby="'home-tab-' + selectedCapability.key" tabindex="0"><div class="home-sample-top"><span>{{ selectedCapability.kind }}</span><span class="home-sample-label">创作示例</span></div><h3>{{ selectedCapability.sampleTitle }}</h3><p>{{ selectedCapability.copy }}</p><div class="home-sample-bottom"><span>{{ selectedCapability.meta }}</span><RouterLink to="/workspace" target="_blank" rel="noopener noreferrer">查看工作台<CreativeIcon type="arrow" /></RouterLink></div></div></div>
      </section>
      <section id="scenarios" class="home-scenarios" aria-labelledby="scenarios-title"><div class="home-wrap"><div class="home-section-heading"><h2 id="scenarios-title">不同品类，同样出彩。</h2><span>创作示例 · 非真实客户案例</span></div><div class="home-scenario-grid"><figure v-for="item in categories" :key="item.key" class="home-scenario"><div class="home-category-photo" :class="'home-category-photo--' + item.key"><img loading="lazy" :src="'/homepage/commerce-categories-v3.png'" :alt="item.alt" width="1536" height="1024"></div><figcaption><h3>{{ item.label }}</h3><p>{{ item.caption }}</p></figcaption></figure></div></div></section>
      <section id="how-it-works" class="home-process home-wrap" aria-labelledby="process-title"><div class="home-section-intro"><h2 id="process-title">创作有灵感，<br>每一步也清楚。</h2><p>资料、要求、费用、成果，始终心中有数。<br>保留你的选择，也让操作更从容。</p></div><ol><li v-for="(step, index) in steps" :key="step.title"><span class="home-step-number">{{ index + 1 }}</span><h3>{{ step.title }}</h3><p>{{ step.description }}</p></li></ol></section>
      <section v-if="cases.length" class="home-public-cases home-wrap" aria-labelledby="cases-title"><div class="home-section-heading"><h2 id="cases-title">真实作品案例</h2><span>已获公开展示授权</span></div><div class="home-case-grid"><article v-for="item in cases" :key="item.id"><h3>授权作品</h3><template v-for="copy in item.items" :key="copy.id"><img v-if="copy.media_type.startsWith('image/')" :src="copy.url" alt="已获公开展示授权的作品" loading="lazy"><video v-else-if="copy.media_type === 'video/mp4'" :src="copy.url" controls preload="none" aria-label="已获授权的视频作品" /><a v-else :href="copy.url" target="_blank" rel="noopener">查看授权文案</a></template></article></div></section>
      <p v-if="busy" class="home-load-status home-wrap" role="status">正在读取公开作品…</p><aside v-if="error" class="home-load-error home-wrap" role="alert"><span>{{ error }}</span><UiButton :disabled="busy" @click="load">重新读取</UiButton></aside>
      <section class="home-final-cta home-wrap" aria-labelledby="cta-title"><div><h2 id="cta-title">下一份精彩，<br>从你的商品开始。</h2><p>给商品好好登场的机会。</p></div><RouterLink class="home-button" :to="session.profile.value ? '/workspace' : '/register'" :target="session.profile.value ? '_blank' : undefined" :rel="session.profile.value ? 'noopener noreferrer' : undefined">{{ session.profile.value ? '进入工作台' : '注册体验' }}<CreativeIcon class="home-diagonal-arrow" type="arrow" /></RouterLink></section>
    </div>
    <footer class="home-footer home-wrap"><a class="home-brand" href="#home-top"><BrandMark class="home-brand-mark" /><span class="brand-name" :title="brandName">{{ brandName }}</span></a><span>电商 AI 创作平台</span><p>商品与创作内容仅作示例展示。</p></footer>
  </div>
</template>
