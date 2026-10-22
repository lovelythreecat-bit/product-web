<script setup lang="ts">
import UiButton from '../../components/ui/UiButton.vue'
import { computed, onMounted, ref } from 'vue'
import * as api from '../../api/site'
import type { Schema } from '../../types/api'
import { useAdminRequest } from '../admin/shared'
import { session } from '../auth/session'
import CreativeIcon from './components/CreativeIcon.vue'
import BrandMark from '../../components/BrandMark.vue'
import UserMenu from '../../components/UserMenu.vue'
import ProductVisual from './components/ProductVisual.vue'
import './homepage.css'

// Unpublished design copy is limited to local development. Production uses API approvals.
const designPreview = import.meta.env.DEV && import.meta.env.MODE !== 'test'
const content = ref<Schema<'SiteContentView'> | null>(null)
const cases = ref<Schema<'PublicCaseView'>[]>([])
const { busy, error, run } = useAdminRequest()
const capabilities = [
  { key: 'text', label: '文案创作', title: '把亮点，写到心动处。', description: '从商品信息到创作要求，让你的卖点表达更有意思。' },
  { key: 'image', label: '图片创作', title: '给商品，一个亮眼的画面。', description: '主图、场景图、海报，换个视角，发现商品的另一面。' },
  { key: 'video', label: '视频创作', title: '让商品故事，动起来。', description: '把商品介绍和图片，变成一支有看点的视频。' },
] as const
const categories = [
  { key: 'fashion', label: '鞋服', caption: '轻盈的日常，也可以很出彩。' },
  { key: 'beauty', label: '美妆', caption: '细节里的美，值得被看见。' },
  { key: 'digital', label: '数码', caption: '换个角度，呈现科技的质感。' },
] as const
const steps = [
  { title: '带上商品素材', description: '准备商品图片、名称、卖点等信息。' },
  { title: '选个创作方向', description: '按需选择文案、图片或视频，并设置创作规格。' },
  { title: '看清费用再开始', description: '提交前，确认本次创作内容与费用。' },
  { title: '收下你的新作品', description: '打开作品库，随时查看、下载。' },
]
const displayedSteps = computed(() => designPreview ? steps : (content.value?.content?.process_steps ?? []).map(title => ({ title, description: '' })))
const approvedHeroImage = computed(() => cases.value.flatMap(item => item.items).find(item => item.media_type.startsWith('image/')))
function load() {
  return run(() => Promise.all([api.getPublicSite(), api.getPublicCases()]), ([site, items]) => {
    content.value = site.content
    cases.value = items
  })
}
onMounted(load)
</script>

<template>
  <div class="site-home" :class="{ 'site-home--preview': designPreview }">
    <header class="home-header">
      <a class="home-brand" href="#home-top" aria-label="映作，返回顶部">
        <BrandMark class="home-brand-mark" />
        <span>映作</span>
      </a>
      <nav class="home-nav" aria-label="首页导航">
        <a v-if="designPreview || content?.content" href="#capabilities">创作能力</a>
        <a v-if="designPreview" href="#scenarios">应用场景</a>
        <a v-if="designPreview || content?.content" href="#how-it-works">工作方式</a>
      </nav>
      <div class="home-account-links"><template v-if="session.profile.value"><RouterLink class="home-button home-button--compact home-workspace-link" to="/workspace" target="_blank" rel="noopener noreferrer">进入工作台</RouterLink><UserMenu /></template><template v-else><RouterLink class="home-login" to="/login">登录</RouterLink><RouterLink class="home-button home-button--compact" to="/register">注册体验</RouterLink></template></div>
    </header>

    <template v-if="designPreview || content?.content">
      <section id="home-top" class="home-hero" aria-labelledby="site-title">
        <div class="home-hero-copy">
          <p v-if="designPreview" class="home-hero-tagline">为电商而生，让创意上场</p>
          <h1 v-if="designPreview" id="site-title">让好商品，<br><em>亮眼登场。</em></h1><h1 v-else id="site-title" class="home-public-title">映作<br><em>电商 AI 创作平台</em></h1>
          <p v-if="designPreview" class="home-hero-lead">想写文案、做图片，还是来支视频？<br class="desktop-break">带上商品素材，选你需要的，让 AI 帮你把灵感做成作品，把商品亮点秀出来。</p><p v-else class="home-hero-lead home-approved-copy">{{ content?.content?.product_intro }}</p>
          <div class="home-hero-actions"><RouterLink class="home-button" to="/register">注册体验<CreativeIcon type="arrow"/></RouterLink><a class="home-text-link" href="#capabilities">看看能创作什么<CreativeIcon type="arrow"/></a></div>
        </div>
        <div class="home-hero-stage" :class="{ 'home-hero-stage--public': !designPreview }" :aria-label="designPreview ? '鞋服、美妆、数码商品与三种创作成果的创作示例' : '文案、图片、视频三种独立创作能力'">
          <img v-if="designPreview" class="home-hero-art" :src="'/homepage/commerce-hero-v3.png'" alt="奶油色运动鞋与卫衣、黑色耳机和琥珀色护肤瓶，悬浮于铜色光轨和展示台上" width="1536" height="1024" fetchpriority="high"><img v-if="!designPreview && approvedHeroImage" class="home-hero-art home-authorized-art" :src="approvedHeroImage.url" alt="已获公开展示授权的作品"><div v-else-if="!designPreview" class="home-public-orbit" aria-hidden="true"><i></i><i></i><i></i><span>AI</span></div>
          <span v-if="designPreview" class="home-category-label home-category-label--fashion">鞋服</span><span v-if="designPreview" class="home-category-label home-category-label--digital">数码</span><span v-if="designPreview" class="home-category-label home-category-label--beauty">美妆</span>
          <div class="home-output home-output--text"><span v-if="designPreview" class="home-example">创作示例</span><p>电商文案</p><strong v-if="designPreview">轻盈设计，<br>陪伴日常步伐。</strong><CreativeIcon v-else type="text"/><div class="home-copy-lines" aria-hidden="true"><i></i><i></i></div></div>
          <div class="home-output home-output--image"><span v-if="designPreview" class="home-example">创作示例</span><p>商品图片</p><ProductVisual v-if="designPreview" kind="fashion"/><CreativeIcon v-else type="image"/></div>
          <div class="home-output home-output--video"><span v-if="designPreview" class="home-example">创作示例</span><p>产品视频</p><ProductVisual v-if="designPreview" kind="digital"/><CreativeIcon v-else type="video"/><span v-if="designPreview" class="home-cover-label">视频封面示意</span></div>
        </div>
      </section>

      <div class="home-capability-strip" aria-label="三种独立创作能力">
        <a v-for="item in capabilities" :key="item.key" :href="'#creation-' + item.key"><CreativeIcon :type="item.key"/><span><strong>{{ item.label.slice(0, 2) }}</strong><small>{{ designPreview ? item.title : '独立选择，分别创作' }}</small></span><CreativeIcon class="strip-arrow" type="arrow"/></a>
      </div>

      <section id="capabilities" class="home-section home-capabilities" aria-labelledby="capabilities-title">
        <div class="home-section-heading"><h2 v-if="designPreview" id="capabilities-title">好商品，<br class="mobile-break">不止一种出场方式。</h2><h2 v-else id="capabilities-title">创作能力</h2><p v-if="designPreview">好商品，<br>值得更好的表达。</p></div>
        <div class="home-creation-grid">
          <article v-for="(item, index) in capabilities" :id="'creation-' + item.key" :key="item.key" class="home-creation">
            <div class="home-creation-heading"><CreativeIcon :type="item.key"/><div><h3>{{ item.label }}</h3><p v-if="designPreview">{{ item.title }}</p></div></div>
            <div v-if="designPreview && item.key === 'text'" class="home-copy-sample"><span v-if="designPreview" class="home-example">创作示例</span><ProductVisual kind="fashion"/><div class="home-copy-sample-text"><strong>轻盈设计，<br>陪伴日常步伐。</strong><p>把寻常的一步，<br>走成自己的风格。</p><span aria-hidden="true"></span></div></div>
            <div v-else-if="designPreview" class="home-media-sample"><ProductVisual :kind="index === 1 ? 'fashion' : 'digital'"/><span v-if="designPreview" class="home-example">创作示例</span><span v-if="item.key === 'video'" class="home-film-caption"><CreativeIcon type="video"/>视频封面示意</span></div>
            <div v-else class="home-approved-cap-art" aria-hidden="true"><CreativeIcon :type="item.key"/></div><p class="home-creation-description home-approved-copy">{{ designPreview ? item.description : content?.content?.agent_descriptions[item.key] }}</p>
          </article>
        </div>
      </section>

      <section v-if="designPreview" id="scenarios" class="home-section home-scenarios" aria-labelledby="scenarios-title">
        <div class="home-section-heading"><div><h2 id="scenarios-title">卖什么，都有创意可聊。</h2><p class="home-section-description">一双鞋、一瓶护肤品、一副耳机……不同商品，都值得有自己的精彩。</p></div></div>
        <div class="home-scenario-grid">
          <article v-for="item in categories" :key="item.key" class="home-scenario"><div class="home-scenario-title"><h3>{{ item.label }}</h3><p>{{ item.caption }}</p></div><ProductVisual :kind="item.key"/><span v-if="designPreview" class="home-example">创作示例</span><div class="home-scenario-footer"><span>{{ item.label }}创意展示</span><span>商品素材 · 画面表达</span></div></article>
        </div>
      </section>

      <section id="how-it-works" class="home-section home-mechanism" aria-labelledby="mechanism-title">
        <h2 v-if="designPreview" id="mechanism-title">带上商品素材，<br class="mobile-break">让灵感有个着落。</h2><h2 v-else id="mechanism-title">商品资料与创作成果</h2>
        <p v-if="designPreview" class="home-section-description">写文案、做图片、创视频，按需选择，分别创作。你定方向，AI 帮你把想法做出来。</p>
        <div class="home-mechanism-diagram" :class="{ 'home-mechanism-diagram--public': !designPreview }">
          <div class="home-source"><h3>商品素材</h3><p>你提供的基础信息</p><div class="home-source-content"><div v-if="designPreview" class="home-source-thumbs"><ProductVisual kind="fashion"/><ProductVisual kind="beauty"/><ProductVisual kind="digital"/></div><div v-else class="home-source-icons" aria-hidden="true"><CreativeIcon type="image"/><CreativeIcon type="text"/></div><ul><li>商品图片</li><li>商品名称</li><li>关键卖点</li><li>其他补充信息</li></ul></div></div>
          <div class="home-branches" aria-hidden="true"><svg viewBox="0 0 100 210" preserveAspectRatio="none"><path d="M0 105C45 105 45 30 100 30M0 105H100M0 105C45 105 45 180 100 180"/><circle cx="98" cy="30" r="2"/><circle cx="98" cy="105" r="2"/><circle cx="98" cy="180" r="2"/></svg></div>
          <div class="home-destinations"><div v-for="item in capabilities" :key="item.key" class="home-destination"><CreativeIcon :type="item.key"/><strong>{{ item.label }}</strong><span>独立选择，分别创作</span><span v-if="designPreview" class="home-example">创作示例</span></div></div>
          <p v-if="designPreview" class="home-mechanism-aside">同一份商品素材，<br>可以生发不同的创作内容。<br><em>让商品表达更丰富。</em></p>
        </div>
      </section>

      <section class="home-section home-process" aria-labelledby="process-title"><h2 v-if="designPreview" id="process-title">从“有个想法”，<br class="mobile-break">到“有份作品”。</h2><h2 v-else id="process-title">使用流程</h2><ol><li v-for="(step, index) in displayedSteps" :key="step.title"><span class="home-step-number">0{{ index + 1 }}</span><div><h3>{{ step.title }}</h3><p>{{ step.description }}</p></div></li></ol><p v-if="designPreview" class="home-library-note">好作品不用翻来翻去，打开作品库，随时查看、下载。</p></section>
    </template>

    <template v-else>
      <section id="home-top" class="home-approved-intro home-section" aria-labelledby="site-title"><h1 id="site-title">映作 · 电商 AI 创作平台</h1><p v-if="content?.content" class="home-approved-copy">{{ content.content.product_intro }}</p><p v-else-if="busy" role="status">正在读取产品介绍…</p><p v-else>产品介绍正在准备中。</p><div class="home-hero-actions"><RouterLink class="home-button" to="/register">注册体验<CreativeIcon type="arrow"/></RouterLink><RouterLink v-if="session.profile.value" class="home-text-link" to="/workspace" target="_blank" rel="noopener noreferrer">进入工作台<CreativeIcon type="arrow"/></RouterLink></div></section>
      <section v-if="content?.content" id="capabilities" class="home-section" aria-labelledby="capabilities-title"><h2 id="capabilities-title">创作能力</h2><div class="home-creation-grid"><article v-for="item in capabilities" :key="item.key"><div class="home-creation-heading"><CreativeIcon :type="item.key"/><h3>{{ item.label }}</h3></div><p class="home-approved-copy">{{ content.content.agent_descriptions[item.key] }}</p></article></div></section>
      <section v-if="content?.content" id="how-it-works" class="home-section" aria-labelledby="process-title"><h2 id="process-title">使用流程</h2><ol class="home-approved-steps"><li v-for="(step, index) in content.content.process_steps" :key="index">{{ step }}</li></ol></section>
    </template>

    <section v-if="!designPreview || cases.length" class="home-section home-public-cases" aria-labelledby="cases-title"><h2 id="cases-title">真实作品案例</h2><p v-if="!cases.length">暂无已获公开展示授权的真实案例。</p><div v-else class="home-case-grid"><article v-for="item in cases" :key="item.id"><h3>授权作品</h3><template v-for="copy in item.items" :key="copy.id"><img v-if="copy.media_type.startsWith('image/')" :src="copy.url" alt="已获公开展示授权的作品" loading="lazy"><video v-else-if="copy.media_type === 'video/mp4'" :src="copy.url" controls preload="none" aria-label="已获授权的视频作品"/><a v-else :href="copy.url" target="_blank" rel="noopener">查看授权文案</a></template></article></div></section>

    <aside v-if="error" class="home-load-error" role="alert"><span>{{ error }}</span><UiButton @click="load">重新读取</UiButton></aside>
    <section v-if="designPreview || content?.content" class="home-final-cta" aria-labelledby="cta-title"><div><h2 v-if="designPreview" id="cta-title">你的商品，<br>下一次怎么出场？</h2><h2 v-else id="cta-title">映作</h2><p v-if="designPreview">带上一个想法，开启下一份创作。</p></div><RouterLink class="home-button" to="/register">注册体验<CreativeIcon type="arrow"/></RouterLink><div class="home-copper-orbit" aria-hidden="true"><i></i><i></i><i></i></div></section>
    <footer class="home-footer"><a class="home-brand" href="#home-top"><BrandMark class="home-brand-mark" /><span>映作</span></a><p v-if="designPreview">商品与创作内容仅作示例展示。</p><RouterLink v-else class="home-login" to="/login">登录</RouterLink></footer>
  </div>
</template>
