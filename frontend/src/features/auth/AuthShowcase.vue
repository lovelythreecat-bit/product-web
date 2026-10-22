<script setup lang="ts">
import { ref } from 'vue'
import BrandMark from '../../components/BrandMark.vue'
import CreativeIcon from '../site/components/CreativeIcon.vue'

// The existing artwork is a development sample, not an approved public case.
const previewArtwork = ref(import.meta.env.DEV)
</script>

<template>
  <aside class="auth-showcase" aria-label="映作电商创作">
    <div class="showcase-copy">
      <h2>让好商品，<br><em>亮眼登场。</em></h2>
      <p>从一份商品素材，<br>开启文案、图片与视频创作。</p>
    </div>
    <figure v-if="previewArtwork" class="showcase-art">
      <img :src="'/homepage/commerce-hero-v3.png'" alt="运动鞋、卫衣、耳机与护肤瓶的商品创作视觉示意" width="1536" height="1024" @error="previewArtwork = false">
      <figcaption>商品创作视觉示意</figcaption>
    </figure>
    <div v-else class="showcase-brand" aria-hidden="true"><BrandMark /><span>映作</span></div>
    <div class="showcase-capabilities" aria-label="创作能力">
      <span><CreativeIcon type="text" />电商文案</span>
      <span><CreativeIcon type="image" />商品图片</span>
      <span><CreativeIcon type="video" />产品视频</span>
    </div>
  </aside>
</template>

<style scoped>
.auth-showcase { display:flex; flex-direction:column; min-width:0; padding:44px 40px 28px; background:var(--color-sidebar); overflow:hidden; }
.showcase-copy { position:relative; z-index:1; }
.showcase-copy h2 { margin:0; font-size:clamp(36px,3.5vw,48px); line-height:1.35; font-weight:650; letter-spacing:-.03em; }
.showcase-copy em { color:var(--color-primary); font-style:normal; }
.showcase-copy p { margin:20px 0 0; font-size:15px; line-height:1.85; }
.showcase-art { position:relative; margin:20px -40px 0; flex:1; min-height:240px; display:flex; align-items:center; }
.showcase-art img { display:block; width:100%; height:auto; mix-blend-mode:multiply; }
.showcase-art figcaption { position:absolute; bottom:8px; right:20px; padding:2px 8px; border-radius:4px; background:var(--color-sidebar); color:var(--color-muted); font-size:12px; }
.showcase-capabilities { display:flex; flex-wrap:wrap; justify-content:space-between; gap:12px; border-top:1px solid var(--color-border); padding-top:24px; margin-top:20px; }
.showcase-capabilities span { display:flex; align-items:center; gap:8px; font-size:13px; color:var(--color-muted); }
.showcase-capabilities svg { width:18px; height:18px; color:var(--color-primary); }
.showcase-brand { flex:1; min-height:280px; display:flex; align-items:center; justify-content:center; gap:24px; color:var(--color-primary); font-size:48px; font-weight:650; }
.showcase-brand :deep(img) { width:104px; height:104px; }
@media (max-width:1000px) { .auth-showcase { padding:36px 28px 24px; } .showcase-art { margin-inline:-28px; } .showcase-capabilities { gap:12px; } .showcase-capabilities span { gap:5px; font-size:12px; } }
@media (max-width:800px) { .auth-showcase { display:none; } }
</style>
