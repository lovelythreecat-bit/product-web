<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import UiButton from '../../components/ui/UiButton.vue'
import BrandMark from '../../components/BrandMark.vue'
import UserMenu from '../../components/UserMenu.vue'
import ThemeToggle from '../../components/ThemeToggle.vue'
import linglingImage from '../../assets/homepage/lingling.png'
import * as api from '../../api/site'
import type { Schema } from '../../types/api'
import { useAdminRequest } from '../admin/shared'
import { session } from '../auth/session'
import { brandName } from './brand'
import { useHomepageMotion } from './useHomepageMotion'
import './homepage.css'

const root = ref<HTMLElement>()
const { paused, reduced, stopped, backgrounded, product, autoStopped, cycleProgress, stage, touring, galleryRunning, slot, selectProduct, selectStage, playStory, galleryKey, tilt, resetTilt } = useHomepageMotion(root)
const entryLink = computed(() => ({ to: session.profile.value ? '/workspace' : '/register', target: session.profile.value ? '_blank' : undefined, rel: session.profile.value ? 'noopener noreferrer' : undefined }))
const guide = ref(0)
const guideCopy = ['卡在哪一步，玲玲就在哪一步。', '主图、详情、海报，输入即出。', '每一步都有人陪你走完，再也不怕「不会用」。', '生成即分发。']
const pro = ref(false)
const workspaceCopy = computed(() => pro.value
  ? '想要完全掌控？专业工作台给你图层、参数、批量与模板。飞马不替你决定，只让你更快。'
  : '专业工作台给老手完整控制权；小白工作台把专业能力收进一句对话——选品类、说卖点、挑风格，智能体替你排兵布阵，零基础也能出品专业级素材。')
// Illustrations never become public cases. The authorized API remains the sole source.
const cases = ref<Schema<'PublicCaseView'>[]>([])
const { busy, error, run } = useAdminRequest()
function load() {
  return run(() => Promise.all([api.getPublicSite(), api.getPublicCases()]), ([, items]) => { cases.value = items })
}
onMounted(load)
</script>

<template>
<div id="home-top" ref="root" class="site-home js-motion" :class="{ paused: stopped, backgrounded }">


<header class="nav">
  <a class="brand" href="#home-top" :aria-label="brandName + '，返回顶部'"><BrandMark /><span :title="brandName">{{ brandName }}</span></a>
  <nav aria-label="首页导航">
<a href="#creation">创作能力</a>
<a href="#lingling">玲玲陪练</a>
<a href="#delivery">多店发布</a>
</nav>
  <div class="nav-actions"><ThemeToggle />
    <template v-if="session.profile.value">
<RouterLink class="button small" to="/workspace" target="_blank" rel="noopener noreferrer">进入工作台</RouterLink><UserMenu /></template>
    <template v-else>
<RouterLink class="plain" to="/login">登录</RouterLink>
<RouterLink class="button small" to="/register">免费开始创作 <span aria-hidden="true">↗</span></RouterLink></template>
  </div>
</header>
<div class="home-main">
<section class="hero hero-v2" aria-labelledby="hero-title">
<div class="hero-layout wrap">
<div class="hero-message">
<h1 id="hero-title"><span class="hero-intro">一站式电商内容工具，</span><span class="hero-title-line">小白<span class="time-emphasis">十分钟<svg viewBox="0 0 300 18" aria-hidden="true"><path d="M3 11 Q140 -5 297 10 M36 16 Q168 4 275 15"/></svg></span></span><strong>高效出片</strong></h1>
<p class="hero-description">文生图搞定传统电商，文生视频拿下抖店带货；专业与小白双工作台并行，AI 数字人玲玲手把手陪你出片，最后一键发到所有店铺。</p>
<div class="hero-primary">
<RouterLink class="button" v-bind="entryLink">免费开始创作 <span aria-hidden="true">↗</span></RouterLink>
<a href="#creation" class="hero-process-link">探索创作能力 <span aria-hidden="true">↓</span></a>
</div>
<RouterLink class="lingling-invite" to="/ai-customer-service" target="_blank" rel="noopener noreferrer" aria-label="看玲玲怎么带你玩（新窗口打开 AI 客服）"><span class="invite-portrait"><img :src="linglingImage" alt="玲玲数字人" width="120" height="180" fetchpriority="high"></span><span class="invite-copy"><small>你的 AI 数字人陪练</small><b>看玲玲怎么带你玩</b><span class="invite-hint">每一步都有人陪</span></span><span class="invite-play" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M9 5 19 12 9 19Z"/></svg></span><span class="invite-wave" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span></RouterLink>
</div>
<div class="hero-showcase" :class="{ 'gallery-stopped': !galleryRunning }" @pointermove="tilt($event, true)" @pointerleave="resetTilt" aria-label="多品类商品创作舞台">
<div class="stage-halo" aria-hidden="true"><i></i><i></i>
</div>
<div class="stage-heading"><span>文生图 <b>×</b> 文生视频</span><span>创作示例</span>
</div>
<div class="orbit-gallery" @keydown="galleryKey" tabindex="0" role="group" aria-label="商品创作画廊，左右方向键或下方品类按钮切换">
<figure class="orbit-card" data-product="0" :data-slot="slot(0)" :aria-hidden="product !== 0">
<div class="orbit-card-photo product shoe" role="img" aria-label="鞋服商品创作示例">
</div>
<div class="canvas-corners" aria-hidden="true">
</div><figcaption><span>文生图</span><b>主图、详情、海报，输入即出。</b></figcaption>
</figure>
<figure class="orbit-card" data-product="1" :data-slot="slot(1)" :aria-hidden="product !== 1">
<div class="orbit-card-photo product beauty" role="img" aria-label="美妆商品创作示例">
</div>
<div class="canvas-corners" aria-hidden="true">
</div><figcaption><span>文生视频</span><b>卖点进，视频出，节奏跟上投放。</b></figcaption>
</figure>
<figure class="orbit-card" data-product="2" :data-slot="slot(2)" :aria-hidden="product !== 2">
<div class="orbit-card-photo product audio" role="img" aria-label="数码商品创作示例">
</div>
<div class="canvas-corners" aria-hidden="true">
</div><figcaption><span>文生图</span><b>传统电商，看图说话出爆款</b></figcaption>
</figure>
<div class="stage-output" aria-hidden="true"><span class="output-play">▶</span><span>抖店带货<br><b>十分钟一条种草片</b></span>
<div class="mini-wave"><i></i><i></i><i></i><i></i><i></i>
</div>
</div>
</div>
<div class="stage-bottom">
<p>从 0 到爆款素材，只差一个飞马。</p>
<div class="showcase-switcher" role="group" aria-label="选择商品创作示例">
<button data-select-product="0" :aria-pressed="product === 0" @click="selectProduct(0)">鞋服</button>
<button data-select-product="1" :aria-pressed="product === 1" @click="selectProduct(1)">美妆</button>
<button data-select-product="2" :aria-pressed="product === 2" @click="selectProduct(2)">数码</button>
<button class="gallery-auto" :disabled="stopped" :aria-label="autoStopped ? '开启商品轮换' : '暂停商品轮换'" :aria-pressed="autoStopped" @click="autoStopped = !autoStopped">{{ autoStopped ? '▷' : 'Ⅱ' }}</button>
</div><span class="stage-cycle" aria-hidden="true"><i :style="{ transform: `scaleX(${cycleProgress})` }"></i></span>
</div>
</div>
</div>
<div class="motion-controls wrap">
<button class="motion-toggle" :disabled="reduced" :aria-pressed="stopped" @click="paused = !paused">{{ reduced ? '系统已减少动效' : paused ? '开启动效' : '暂停动效' }}</button>
</div>
<div class="capability-line"><span>文生图</span><i></i><span>文生视频</span><i></i><span>小白工作台</span><i></i><span>玲玲陪练</span><i></i><span>一键多发</span>
</div>
</section>
<section class="story" id="creation" aria-labelledby="story-title">
<div class="story-pin">
<div class="story-inner">
<div class="story-copy">
<h2 id="story-title">电商人的 AI 内容工厂<span>从想法到出片，<br>只隔一次对话。</span></h2>
<p>面向传统电商卖家与抖店带货玩家，把文生图、文生视频、智能体引导、数字人陪练、多店分发，收进同一个工作台。</p>
<div class="steps" role="group" aria-label="创作演示步骤">
<button class="step" :class="{ active: stage === 0 }" data-step="0" :aria-pressed="stage === 0" @click="selectStage(0)"><span>01</span>选品类、说卖点、挑风格 <i>↗</i></button>
<button class="step" :class="{ active: stage === 1 }" data-step="1" :aria-pressed="stage === 1" @click="selectStage(1)"><span>02</span>主图、详情、海报 <i>↗</i></button>
<button class="step" :class="{ active: stage === 2 }" data-step="2" :aria-pressed="stage === 2" @click="selectStage(2)"><span>03</span>口播、种草、测评 <i>↗</i></button>
</div>
<button class="text-button" id="story-play" :aria-pressed="touring" @click="playStory">{{ stopped ? '下一步演示 →' : touring ? '暂停演示 Ⅱ' : '播放创作演示 ▷' }}</button>
<p class="story-hint">向下滚动，展开创作过程</p>
</div>
<div class="story-screen" :data-stage="stage">
<div class="screen-top"><span><i></i> {{ brandName }}</span><span>创作示例</span>
</div>
<div class="scene scene-input" :inert="stage !== 0" :aria-hidden="stage !== 0">
<div class="source-product product tumbler" role="img" aria-label="浅蓝通勤保温杯白底商品示例">
</div>
<div class="source-caption"><span>文生图</span>
<h3>输入商品，飞马出图。</h3>
<div class="chips"><span>主图</span><span>详情页</span><span>卖点海报</span>
</div>
</div>
</div>
<div class="scene scene-images" :inert="stage !== 1" :aria-hidden="stage !== 1">
<div class="output-photo back-photo product tumbler" role="img" aria-label="同款保温杯主图示例">
</div>
<div class="output-photo mid-photo product tumbler-detail" role="img" aria-label="同款保温杯杯盖与材质细节示例">
</div>
<div class="output-photo front-photo product commute" role="img" aria-label="同款保温杯通勤办公场景海报示例">
</div>
<div class="output-caption">
<h3>传统电商，看图说话出爆款</h3>
<p>主图、详情、海报，输入即出。</p>
</div>
</div>
<div class="scene scene-video" :inert="stage !== 2" :aria-hidden="stage !== 2">
<div class="video-frame">
<div class="product creator" role="img" aria-label="人物讲解同款保温杯的带货视频分镜示例">
</div>
<div class="video-title">抖店带货，<br>十分钟一条种草片</div>
<div class="video-label">动态分镜示意</div>
<div class="film-progress"><i></i>
</div>
</div>
<div class="video-side"><span>文生视频</span>
<p>卖点进，<br>视频出，<br>节奏跟上投放。</p>
<div class="timeline" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i>
</div>
</div>
</div>
<div class="scene-track" aria-hidden="true"><i></i><i></i><i></i>
</div>
</div>
</div>
</div>
</section>
<section class="abilities wrap" aria-labelledby="abilities-title">
<div class="section-heading reveal">
<h2 id="abilities-title">传统电商的爆款流水线</h2>
<p>输入商品，飞马出图。主图、详情页、卖点海报、活动 banner，AI 一次生成多角度方案，传统电商上架不再等设计。</p>
</div>
<div class="gallery">
<figure class="gallery-item tilt" @pointermove="tilt($event)" @pointerleave="resetTilt">
<div class="product shoe" role="img" aria-label="鞋服主图创作示例">
</div><figcaption><span>文生图</span><b>传统电商，看图说话出爆款</b></figcaption>
</figure>
<figure class="gallery-item tilt" @pointermove="tilt($event)" @pointerleave="resetTilt">
<div class="product beauty" role="img" aria-label="美妆商品创作示例">
</div><figcaption><span>主图、详情、海报</span><b>输入即出。</b></figcaption>
</figure>
<figure class="gallery-item tilt" @pointermove="tilt($event)" @pointerleave="resetTilt">
<div class="product audio" role="img" aria-label="数码商品创作示例">
</div><figcaption><span>创作示例</span><b>不会设计？飞马替你想好了。</b></figcaption>
</figure>
</div>
<div class="video-feature reveal">
<div class="video-feature-copy">
<h2>抖店带货的<br>流量引擎</h2>
<p>一句话描述卖点，飞马生成带货短视频。口播、种草、测评多风格任选，适配抖音 / 抖店投放节奏，视频带货从想创意到出片只隔十分钟。</p>
<a class="text-button" href="#creation">十分钟做第一条带货视频 <span aria-hidden="true">↗</span></a>
</div>
<div class="reel" aria-label="视频带货动态分镜示意">
<div class="reel-picture product creator" role="img" aria-label="人物口播讲解保温杯的种草视频分镜示例">
</div>
<div class="reel-caption"><span>动态分镜示意</span>
<h3>流量窗口不等人，<br>飞马让你每天都有新片子。</h3>
<div class="timeline" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i>
</div>
</div>
</div>
</div>
</section>
<section class="lingling" id="lingling">
<div class="lingling-inner wrap">
<div class="character-stage">
<div class="orbit orbit-one">
</div>
<div class="orbit orbit-two">
</div><span class="character-name" aria-hidden="true">玲玲</span><img class="character" :src="linglingImage" alt="玲玲 AI 数字人陪练，白粉色长发、蓝粉色衣服" loading="lazy">
<div class="speech" id="speech" aria-live="polite">{{ guideCopy[guide] }}</div>
</div>
<div class="lingling-copy">
<h2>你不需要会设计，<br><strong>只需要会说话。</strong></h2>
<p>AI 数字人客服玲玲实时指路，操作有卡点就开口问，每一步都有人陪你走完，再也不怕「不会用」。</p>
<div class="guide-steps" role="group" aria-label="玲玲陪练步骤">
<button :aria-pressed="guide === 0" data-guide="0" @click="guide = 0">选风格</button><span aria-hidden="true">→</span>
<button :aria-pressed="guide === 1" data-guide="1" @click="guide = 1">出图 / 出视频</button><span aria-hidden="true">→</span>
<button :aria-pressed="guide === 2" data-guide="2" @click="guide = 2">微调</button><span aria-hidden="true">→</span>
<button :aria-pressed="guide === 3" data-guide="3" @click="guide = 3">发布</button>
</div>
<RouterLink class="button" v-bind="entryLink">小白也能用，试试看 <span aria-hidden="true">↗</span></RouterLink>
</div>
</div>
</section>
<section class="workspace-section wrap">
<div class="section-heading">
<h2>专业与小白，各得其法</h2>
<div class="workspace-switch" role="group" aria-label="选择工作台介绍">
<button data-workspace="beginner" :aria-pressed="pro === false" @click="pro = false">小白工作台</button>
<button data-workspace="pro" :aria-pressed="pro === true" @click="pro = true">专业工作台</button>
</div>
</div>
<div class="workspace-demo">
<div class="workspace-description">
<h3 id="workspace-title">{{ pro ? '想要完全掌控？' : '零基础，对话即出片' }}</h3>
<p id="workspace-copy">{{ workspaceCopy }}</p>
</div>
<div class="workspace-visual" id="workspace-visual" :class="{ 'is-pro': pro }">
<div class="mini-conversation"><span>小白工作台</span>
<p>我要卖一款保温杯，主打上班通勤</p>
<section class="workspace-result" aria-label="保温杯创作示例">
<figure><div class="product tumbler" role="img" aria-label="保温杯白底商品图"></div><figcaption>商品主图 · 创作示例</figcaption></figure>
<figure><div class="product commute" role="img" aria-label="保温杯通勤办公场景图"></div><figcaption>通勤场景 · 创作示例</figcaption></figure>
</section>
<div>选风格 <span>→</span> 出图 / 出视频 <span>→</span> 微调 <span>→</span> 发布</div>
</div>
<div class="mini-pro"><span>专业工作台</span>
<div class="pro-tools"><b>图层</b><b>参数</b><b>批量</b><b>模板</b>
</div>
<p>飞马不替你决定，只让你更快。</p>
</div>
</div>
</div>
</section>
<section class="delivery wrap" id="delivery">
<div class="delivery-copy">
<h2>一键多店发布<br><strong>素材即生产力</strong></h2>
<p>生成即分发。一套素材，一键同步到多个店铺后台，省去反复上传、格式调整的重复劳动，出片与上新同频。</p>
</div>
<div class="delivery-diagram" aria-label="一套素材分发到多个店铺的概念示意">
<div class="delivery-source"><BrandMark /><span>一套素材</span>
</div>
<div class="routes" aria-hidden="true"><i></i><i></i><i></i>
</div>
<div class="shops"><span>店铺 01</span><span>店铺 02</span><span>店铺 03</span>
</div>
</div>
</section>
      <section v-if="cases.length" class="home-public-cases wrap" aria-labelledby="cases-title">
<div class="section-heading">
<h2 id="cases-title">真实作品案例</h2><span>已获公开展示授权</span>
</div>
<div class="home-case-grid"><article v-for="item in cases" :key="item.id">
<h3>授权作品</h3><template v-for="copy in item.items" :key="copy.id"><img v-if="copy.media_type.startsWith('image/')" :src="copy.url" alt="已获公开展示授权的作品" loading="lazy"><video v-else-if="copy.media_type === 'video/mp4'" :src="copy.url" controls preload="none" aria-label="已获授权的视频作品" />
<a v-else :href="copy.url" target="_blank" rel="noopener">查看授权文案</a></template></article>
</div>
</section>
      <p v-if="busy" class="home-load-status wrap" role="status">正在读取公开作品…</p><aside v-if="error" class="home-load-error wrap" role="alert"><span>{{ error }}</span><UiButton :disabled="busy" @click="load">重新读取</UiButton></aside>

<section class="closing">
<div class="wrap">
<h2>别再为出片发愁。<br>飞马，让你专心卖货。</h2>
<RouterLink class="button light" v-bind="entryLink">立即免费体验 <span aria-hidden="true">↗</span></RouterLink>
<p>让每个电商人，都拥有自己的内容工厂。</p>
</div>
</section>
</div>
<footer class="footer wrap">
<div class="brand"><BrandMark /><span>{{ brandName }}</span>
</div>
<button class="motion-toggle" :disabled="reduced" :aria-pressed="stopped" @click="paused = !paused">{{ reduced ? '系统已减少动效' : paused ? '开启动效' : '暂停动效' }}</button>
<a href="#home-top">回到顶部 ↑</a>
</footer>

</div>
</template>
