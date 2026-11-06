<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import UiButton from '../../components/ui/UiButton.vue'
import BrandMark from '../../components/BrandMark.vue'
import UserMenu from '../../components/UserMenu.vue'
import ThemeToggle from '../../components/ThemeToggle.vue'
import { theme } from '../../styles/theme'
import * as api from '../../api/site'
import type { Schema } from '../../types/api'
import { useAdminRequest } from '../admin/shared'
import { session } from '../auth/session'
import { brandName } from './brand'
import { useHomepageMotion } from './useHomepageMotion'
import './homepage.css'

const root = ref<HTMLElement>()
const { stopped, backgrounded, product, stage, slot, selectProduct, selectStage, galleryKey, tilt, resetTilt } = useHomepageMotion(root)
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
<div ref="root" class="site-home" :data-theme="theme" :class="{ paused: stopped, backgrounded }">

<svg class="svg-defs" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<symbol id="home-arrow" viewBox="0 0 24 24">
<path d="M5 19 19 5M5 5h14v14"/>
</symbol>
<symbol id="home-play" viewBox="0 0 24 24">
<path d="m9 5 10 7-10 7Z"/>
</symbol>
</svg>
<a class="skip" href="#homepage-content">跳到主要内容</a>
<header class="nav">
<a class="brand" href="#top">
<BrandMark />
<span>{{ brandName }}</span>
</a>
<nav aria-label="主导航">
<a href="#creation">创作能力</a>
<a href="#lingling">玲玲陪练</a>
<a href="#delivery">多店发布</a>
</nav>
<div class="nav-actions">
<ThemeToggle />
<template v-if="session.profile.value">
<RouterLink class="button compact" to="/workspace" target="_blank" rel="noopener noreferrer">进入工作台<svg aria-hidden="true">
<use href="#home-arrow"/>
</svg>
</RouterLink>
<UserMenu />
</template>
<template v-else>
<RouterLink class="login" to="/login">登录</RouterLink>
<RouterLink class="button compact" to="/register">免费开始创作<svg aria-hidden="true">
<use href="#home-arrow"/>
</svg>
</RouterLink>
</template>
</div>
</header>
<div id="homepage-content" class="home-main">
<section class="hero" id="top" aria-labelledby="hero-title">
<div class="hero-aura" aria-hidden="true">
</div>
<div class="hero-head wrap">
<h1 id="hero-title">
<span>一站式电商内容工具，</span>小白十分钟<strong>高效出片</strong>
</h1>
<div class="hero-intro">
<p>文生图搞定传统电商，文生视频拿下抖店带货；专业与小白双工作台并行，AI 数字人玲玲手把手陪你出片，最后一键发到所有店铺。</p>
<RouterLink class="button" v-bind="entryLink">免费开始创作<svg aria-hidden="true">
<use href="#home-arrow"/>
</svg>
</RouterLink>
</div>
</div>
<div class="lightfield" aria-label="商品光场，选择品类查看创作示例">
<canvas id="field" aria-hidden="true">
</canvas>
<div class="field-word" aria-hidden="true">CREATE</div>
<div class="orbit-system" @keydown="galleryKey" @pointermove="tilt" @pointerleave="resetTilt" role="group" aria-label="商品创作舞台，左右方向键切换" tabindex="0">
<figure class="product-plane" data-product="0" :data-slot="slot(0)">
<img src="../../assets/homepage/photo-v3/phone-campaign.webp" alt="冰蓝钛金属手机纸艺布景广告创作示例" fetchpriority="high">
<div class="scan" aria-hidden="true">
</div>
<figcaption>
<span>文生图 · 手机</span>
<b>主图、详情、海报，输入即出。</b>
</figcaption>
<i class="corner tl">
</i>
<i class="corner br">
</i>
</figure>
<figure class="product-plane" data-product="1" :data-slot="slot(1)">
<img src="../../assets/homepage/photo-v3/beauty-campaign.webp" alt="精华瓶与压纹玻璃的美妆广告创作示例">
<div class="scan" aria-hidden="true">
</div>
<figcaption>
<span>文生图 · 美妆</span>
<b>不会设计？飞马替你想好了。</b>
</figcaption>
<i class="corner tl">
</i>
<i class="corner br">
</i>
</figure>
<figure class="product-plane" data-product="2" :data-slot="slot(2)">
<img src="../../assets/homepage/photo-v3/audio-campaign.webp" alt="头戴耳机与纸张布景的音频广告创作示例">
<div class="scan" aria-hidden="true">
</div>
<figcaption>
<span>文生图 · 音频</span>
<b>传统电商，看图说话出爆款</b>
</figcaption>
<i class="corner tl">
</i>
<i class="corner br">
</i>
</figure>
</div>
<div class="field-controls">
<div class="category-switch" role="group" aria-label="选择商品品类">
<button data-select="0" :aria-pressed="product === 0" @click="selectProduct(0)">手机</button>
<button data-select="1" :aria-pressed="product === 1" @click="selectProduct(1)">美妆</button>
<button data-select="2" :aria-pressed="product === 2" @click="selectProduct(2)">音频</button>
</div>
</div>
</div>
<div class="hero-foot wrap">
<RouterLink class="lingling-link" to="/ai-customer-service" target="_blank" rel="noopener">
<img src="../../assets/homepage/lingling.png" alt="玲玲数字人陪练">
<span>
<b>看玲玲怎么带你玩</b>
</span>
<svg aria-hidden="true">
<use href="#home-play"/>
</svg>
</RouterLink>
<p>从 0 到爆款素材，<br>
<strong>只差一个飞马。</strong>
</p>
</div>
</section>
<section class="creation" id="creation" aria-labelledby="creation-title">
<div class="creation-pin wrap">
<div class="section-heading">
<h2 id="creation-title">从想法到出片，<br>
<strong>只隔一次对话。</strong>
</h2>
<p>电商人的 AI 内容工厂。<br>选品类、说卖点、挑风格，让创意一步步成形。</p>
</div>
<div class="creation-layout">
<div class="story-steps" role="group" aria-label="创作演示步骤">
<button data-step="0" :aria-pressed="stage === 0" @click="selectStage(0)">
<span>01</span>
<div>
<b>输入商品，飞马出图。</b>
<small>选品类、说卖点、挑风格</small>
</div>
<svg aria-hidden="true">
<use href="#home-arrow"/>
</svg>
</button>
<button data-step="1" :aria-pressed="stage === 1" @click="selectStage(1)">
<span>02</span>
<div>
<b>主图、详情、海报</b>
<small>不会设计？飞马替你想好了。</small>
</div>
<svg aria-hidden="true">
<use href="#home-arrow"/>
</svg>
</button>
<button data-step="2" :aria-pressed="stage === 2" @click="selectStage(2)">
<span>03</span>
<div>
<b>口播、种草、测评</b>
<small>卖点进，视频出，节奏跟上投放。</small>
</div>
<svg aria-hidden="true">
<use href="#home-arrow"/>
</svg>
</button>
</div>
<div class="creation-stage" :data-stage="stage">
<div class="stage-toolbar">
<span>商品 → 视觉 → 分镜</span>
</div>
<div class="scene scene-zero" :aria-hidden="stage !== 0" :inert="stage !== 0">
<img src="../../assets/homepage/photo-v3/phone-source.webp" alt="冰蓝钛金属影像手机商品原图" loading="lazy">
<div class="prompt">
<span>上传的商品原图</span>
<p>我要卖一款手机，<br>做一组新品广告</p>
<svg aria-hidden="true">
<use href="#home-arrow"/>
</svg>
</div>
</div>
<div class="scene scene-one" :aria-hidden="stage !== 1" :inert="stage !== 1">
<img class="result-a" src="../../assets/homepage/photo-v3/phone-campaign.webp" alt="同款手机纸艺布景广告创作示例" loading="lazy">
<img class="result-b" src="../../assets/homepage/photo-v3/phone-detail.webp" alt="同款手机镜头与金属工艺细节创作示例" loading="lazy">
<div class="scene-caption">主图、详情、海报，输入即出。</div>
</div>
<div class="scene scene-two" :aria-hidden="stage !== 2" :inert="stage !== 2">
<img src="../../assets/homepage/photo-v3/phone-creator.webp" alt="人物讲解同款影像手机的口播分镜示例" loading="lazy">
<div class="video-frame-lines" aria-hidden="true">
</div>
<div class="scene-caption">
<span>动态分镜示意</span>
<b>抖店带货，十分钟一条种草片</b>
<div class="wave" aria-hidden="true">
<i>
</i>
<i>
</i>
<i>
</i>
<i>
</i>
<i>
</i>
<i>
</i>
<i>
</i>
<i>
</i>
<i>
</i>
<i>
</i>
</div>
</div>
</div>
<div class="stage-line" aria-hidden="true">
</div>
</div>
</div>
</div>
</section>
<section class="showroom wrap" id="showroom">
<div class="section-heading">
<h2>传统电商的<br>
<strong>爆款流水线</strong>
</h2>
<p>输入商品，飞马出图。主图、详情页、卖点海报、活动 banner，AI 一次生成多角度方案，传统电商上架不再等设计。</p>
</div>
<div class="showroom-grid">
<figure class="showcase-main">
<img src="../../assets/homepage/photo-v3/shoe-campaign.webp" alt="蓝白跑鞋海报创作示例" loading="lazy">
<figcaption>
<span>鞋服</span>
<h3>让好商品，<br>亮眼登场。</h3>
</figcaption>
</figure>
<div class="showcase-side">
<figure>
<img src="../../assets/homepage/photo-v3/beauty-campaign.webp" alt="美妆商品海报创作示例" loading="lazy">
<figcaption>主图、详情、海报</figcaption>
</figure>
<figure>
<img src="../../assets/homepage/photo-v3/audio-campaign.webp" alt="耳机海报创作示例" loading="lazy">
<figcaption>输入即出。</figcaption>
</figure>
</div>
</div>
</section>
<section class="film">
<div class="film-visual">
<img src="../../assets/homepage/photo-v3/phone-creator.webp" alt="虚构人物讲解影像手机的口播分镜示例" loading="lazy">
<div class="film-aperture" aria-hidden="true">
</div>
<div class="film-label">动态分镜示意</div>
</div>
<div class="film-copy wrap">
<h2>抖店带货的<br>
<strong>流量引擎</strong>
</h2>
<p>一句话描述卖点，飞马生成带货短视频。口播、种草、测评多风格任选，适配抖音 / 抖店投放节奏。</p>
<a class="button" href="#creation">十分钟做第一条带货视频<svg aria-hidden="true">
<use href="#home-arrow"/>
</svg>
</a>
<p class="film-ending">流量窗口不等人，<br>飞马让你每天都有新片子。</p>
</div>
</section>
<section class="guide wrap" id="lingling">
<div class="guide-art">
<div class="guide-ring" aria-hidden="true">
</div>
<span class="guide-word" aria-hidden="true">玲玲</span>
<img src="../../assets/homepage/lingling.png" alt="玲玲 AI 数字人陪练，白粉色长发、蓝粉色衣服" loading="lazy">
<p id="guide-speech" aria-live="polite">{{ guideCopy[guide] }}</p>
</div>
<div class="guide-copy">
<h2>你不需要会设计，<br>
<strong>只需要会说话。</strong>
</h2>
<p>AI 数字人客服玲玲实时指路，操作有卡点就开口问，每一步都有人陪你走完，再也不怕「不会用」。</p>
<div class="guide-steps" role="group" aria-label="玲玲陪练演示">
<button data-guide="0" :aria-pressed="guide === 0" @click="guide = 0">选风格</button>
<button data-guide="1" :aria-pressed="guide === 1" @click="guide = 1">出图 / 出视频</button>
<button data-guide="2" :aria-pressed="guide === 2" @click="guide = 2">微调</button>
<button data-guide="3" :aria-pressed="guide === 3" @click="guide = 3">发布</button>
</div>
<RouterLink class="button" to="/ai-customer-service" target="_blank" rel="noopener">看玲玲怎么带你玩<svg aria-hidden="true">
<use href="#home-arrow"/>
</svg>
</RouterLink>
</div>
</section>
<section class="workspace wrap">
<div class="section-heading">
<h2>专业与小白，<br>
<strong>各得其法。</strong>
</h2>
<div class="workspace-switch" role="group" aria-label="工作台介绍">
<button data-workspace="beginner" :aria-pressed="!pro" @click="pro = false">小白工作台</button>
<button data-workspace="pro" :aria-pressed="pro" @click="pro = true">专业工作台</button>
</div>
</div>
<div class="workspace-demo">
<div>
<h3 id="workspace-title">{{ pro ? '想要完全掌控？' : '零基础，对话即出片' }}</h3>
<p id="workspace-copy">{{ workspaceCopy }}</p>
<span class="workspace-note">工作台概念示意</span>
</div>
<div class="workspace-output" :class="{ 'is-pro': pro }">
<p id="workspace-prompt">{{ pro ? '飞马不替你决定，只让你更快。' : '我要卖一款手机，做一组新品广告' }}</p>
<div class="workspace-images">
<img src="../../assets/homepage/photo-v3/phone-campaign.webp" alt="手机新品广告创作示例" loading="lazy">
<img src="../../assets/homepage/photo-v3/phone-detail.webp" alt="手机工艺细节创作示例" loading="lazy">
</div>
<div class="pro-options" v-if="pro">
<span>图层</span>
<span>参数</span>
<span>批量</span>
<span>模板</span>
</div>
</div>
</div>
</section>
<section class="delivery wrap" id="delivery">
<div>
<h2>一键多店发布<br>
<strong>素材即生产力</strong>
</h2>
<p>生成即分发。一套素材，一键同步到多个店铺后台，省去反复上传、格式调整的重复劳动，出片与上新同频。</p>
</div>
<div class="distribution" aria-label="一套素材分发到三家店铺的概念示意">
<div class="source">
<BrandMark />
<span>一套素材</span>
</div>
<svg viewBox="0 0 360 220" aria-hidden="true">
<path d="M0 110H65Q100 110 120 45T200 35H360M0 110H360M0 110H65Q100 110 120 175T200 185H360"/>
<path class="flow" d="M0 110H65Q100 110 120 45T200 35H360M0 110H360M0 110H65Q100 110 120 175T200 185H360"/>
</svg>
<div class="shops">
<span>店铺 01</span>
<span>店铺 02</span>
<span>店铺 03</span>
</div>
</div>
</section>
<section v-if="cases.length" class="home-public-cases wrap" aria-labelledby="cases-title">
<div class="section-heading">
<h2 id="cases-title">真实作品案例</h2>
<span>已获公开展示授权</span>
</div>
<div class="home-case-grid">
<article v-for="item in cases" :key="item.id">
<h3>授权作品</h3>
<template v-for="copy in item.items" :key="copy.id">
<img v-if="copy.media_type.startsWith('image/')" :src="copy.url" alt="已获公开展示授权的作品" loading="lazy">
<video v-else-if="copy.media_type === 'video/mp4'" :src="copy.url" controls preload="none" aria-label="已获授权的视频作品" />
<a v-else :href="copy.url" target="_blank" rel="noopener">查看授权文案</a>
</template>
</article>
</div>
</section>
      <p v-if="busy" class="home-load-status wrap" role="status">正在读取公开作品…</p>
<aside v-if="error" class="home-load-error wrap" role="alert">
<span>{{ error }}</span>
<UiButton :disabled="busy" @click="load">重新读取</UiButton>
</aside>

<section class="closing">
<div class="closing-orbit" aria-hidden="true">
</div>
<div class="wrap">
<h2>别再为出片发愁。<br>飞马，让你专心卖货。</h2>
<RouterLink class="button" v-bind="entryLink">立即免费体验<svg aria-hidden="true">
<use href="#home-arrow"/>
</svg>
</RouterLink>
<p>让每个电商人，都拥有自己的内容工厂。</p>
</div>
</section>
</div>
<footer class="wrap">
<a class="brand" href="#top">
<BrandMark />
<span>{{ brandName }}</span>
</a>
<a href="#top">回到顶部 ↑</a>
</footer>
</div>
</template>
