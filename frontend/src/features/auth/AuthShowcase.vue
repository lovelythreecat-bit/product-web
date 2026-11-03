<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { brandName } from '../site/brand'
import BrandMark from '../../components/BrandMark.vue'
import CreativeIcon from '../site/components/CreativeIcon.vue'
import { theme } from '../../styles/theme'
import lightArtwork from '../../assets/auth/product-stage-light.webp'
import darkArtwork from '../../assets/auth/product-stage-dark.webp'

// Approved auth artwork is bundled in development and production, never a customer case.
const artworkFailed = ref(false)
const showcase = ref<HTMLElement>()
const stage = ref<HTMLElement>()
const userPaused = ref(false)
const suspended = ref(true)
const reducedMotion = ref(false)
const paused = computed(() => userPaused.value || suspended.value || reducedMotion.value)
let finePointer: MediaQueryList | undefined
let cleanup = () => {}

function resetTilt() {
  stage.value?.style.setProperty('--tilt-x', '0deg')
  stage.value?.style.setProperty('--tilt-y', '0deg')
}
function tilt(event: PointerEvent) {
  if (paused.value || !finePointer?.matches || !stage.value) return
  const bounds = stage.value.getBoundingClientRect()
  stage.value.style.setProperty('--tilt-x', `${((.5 - (event.clientY - bounds.top) / bounds.height) * 5).toFixed(2)}deg`)
  stage.value.style.setProperty('--tilt-y', `${(((event.clientX - bounds.left) / bounds.width - .5) * 7).toFixed(2)}deg`)
}
function toggleMotion() { userPaused.value = !userPaused.value; resetTilt() }
onMounted(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)')
  const desktop = matchMedia('(min-width: 801px)')
  finePointer = matchMedia('(hover: hover) and (pointer: fine)')
  let visible = true
  const sync = () => {
    reducedMotion.value = reduced.matches
    suspended.value = document.hidden || !desktop.matches || !visible
    if (paused.value) resetTilt()
  }
  const observer = new IntersectionObserver(entries => { visible = entries[0]?.isIntersecting ?? false; sync() })
  if (showcase.value) observer.observe(showcase.value)
  reduced.addEventListener('change', sync)
  desktop.addEventListener('change', sync)
  document.addEventListener('visibilitychange', sync)
  sync()
  cleanup = () => {
    observer.disconnect()
    reduced.removeEventListener('change', sync)
    desktop.removeEventListener('change', sync)
    document.removeEventListener('visibilitychange', sync)
  }
})
onBeforeUnmount(() => { cleanup(); finePointer = undefined })
</script>

<template>
  <aside ref="showcase" class="auth-showcase" :aria-label="brandName + '电商创作'" :data-paused="paused">
    <button v-if="!reducedMotion" class="motion-toggle" type="button" :aria-label="userPaused ? '播放展示动画' : '暂停展示动画'" :aria-pressed="userPaused" @click="toggleMotion">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="userPaused ? 'm8 5 11 7-11 7Z' : 'M9 5v14M15 5v14'" /></svg>
    </button>
    <div class="showcase-copy">
      <h2>让好商品，<br><em>亮眼登场。</em></h2>
      <p>从一份商品素材，<br>开启文案、图片与视频创作。</p>
    </div>
    <div ref="stage" class="creative-stage" @pointermove="tilt" @pointerleave="resetTilt">
      <div class="orbit" aria-hidden="true" />
      <div class="stage-depth">
        <div class="art">
          <img v-if="!artworkFailed" class="showcase-art" :src="theme === 'dark' ? darkArtwork : lightArtwork" alt="白色运动鞋、耳机与护肤瓶的商品创作示例" width="1200" height="1312" decoding="async" @error="artworkFailed = true">
          <div v-else class="showcase-brand" aria-hidden="true"><BrandMark /><span>{{ brandName }}</span></div>
          <span class="picture-label"><CreativeIcon type="image" />商品图片</span>
          <span v-if="!artworkFailed" class="showcase-caption">创作示例</span>
        </div>
        <div class="copy-sample"><span class="sample-label"><CreativeIcon type="text" />电商文案</span><p class="sample-text">让每一步，都出彩。</p><span class="sample-note">文案创作示例</span></div>
        <div class="video-sample"><CreativeIcon type="video" /><div><strong>产品视频</strong><span class="video-frames" aria-hidden="true"><i v-for="n in 8" :key="n" /></span></div></div>
      </div>
    </div>
    <div class="showcase-capabilities" aria-label="创作能力">
      <span><CreativeIcon type="text" />电商文案</span>
      <span><CreativeIcon type="image" />商品图片</span>
      <span><CreativeIcon type="video" />产品视频</span>
    </div>
  </aside>
</template>

<style scoped>
.auth-showcase{position:relative;display:flex;flex-direction:column;background:var(--auth-scene);border-radius:10px;overflow:hidden;min-width:0}
.showcase-copy{padding:36px 40px 0;position:relative;z-index:1}
.showcase-copy h2{font-size:42px;line-height:1.3;letter-spacing:-.03em;font-weight:650;margin:0}
.showcase-copy h2 em{font-style:normal;color:var(--color-primary)}
.showcase-copy p{font-size:14px;line-height:1.8;color:var(--color-muted);margin:16px 0 0}
.showcase-art{display:block;position:absolute;width:100%;height:100%;object-fit:cover;object-position:center bottom}
.showcase-caption{position:absolute;bottom:14px;right:18px;z-index:1;background:var(--color-panel);color:var(--color-muted);font-size:11px;padding:3px 8px;border-radius:4px}
.showcase-capabilities{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:21px 32px;background:var(--auth-scene);border-top:1px solid var(--color-border)}
.showcase-capabilities span{display:flex;align-items:center;gap:8px;color:var(--color-muted);font-size:12px}
.showcase-capabilities svg{color:var(--color-primary);width:17px;height:17px}

.creative-stage{position:relative;flex:1;min-height:340px;perspective:1000px;--tilt-x:0deg;--tilt-y:0deg}

.stage-depth{position:absolute;inset:0;transform:rotateX(var(--tilt-x)) rotateY(var(--tilt-y));transition:transform .65s cubic-bezier(.16,1,.3,1);transform-style:preserve-3d}

.art{position:absolute;inset:14px 20% 22px 12%;min-height:0;margin:0;border-radius:14px;overflow:hidden;background:var(--color-panel);box-shadow:0 24px 42px -18px #18284355;transform:rotate(-4deg)}

.showcase-art{object-position:center bottom}
.art .showcase-caption{bottom:12px;right:12px}
.picture-label{position:absolute;top:14px;left:14px;display:flex;align-items:center;gap:7px;padding:6px 10px;background:var(--color-panel);border-radius:8px;font-size:11px;color:var(--color-primary)}
.picture-label svg{width:16px;height:16px}

.copy-sample{position:absolute;z-index:2;left:22px;bottom:12px;width:246px;padding:15px 18px;background:var(--color-panel);border-radius:12px;box-shadow:0 14px 32px -14px #18284360;transform:rotate(3deg)}

.sample-label{display:flex;align-items:center;gap:7px;color:var(--color-muted);font-size:11px}
.sample-label svg{color:var(--color-primary);width:15px;height:15px}
.sample-text{margin:10px 0 3px;font-size:19px;font-weight:600;letter-spacing:-.02em;white-space:nowrap;clip-path:inset(0)}
.sample-note{font-size:11px;color:var(--color-muted)}

.video-sample{position:absolute;z-index:2;right:18px;top:4px;display:flex;align-items:center;gap:11px;padding:13px 16px;background:var(--color-primary);color:var(--color-on-primary);border-radius:12px;box-shadow:0 12px 24px -14px #18284370;transform:rotate(5deg)}
.video-sample>svg{width:30px;height:30px}
.video-sample strong{display:block;font-size:12px;font-weight:600}
.video-frames{display:flex;align-items:center;gap:3px;margin-top:6px;height:10px}
.video-frames i{display:block;width:5px;height:6px;border-radius:2px;background:currentColor;opacity:.65;transform:scaleY(1)}
.video-frames i:nth-child(2n){height:10px}

.orbit{position:absolute;width:80%;height:68%;left:10%;top:16%;border:1px solid var(--color-primary);opacity:.14;border-radius:50%;transform:rotate(-18deg);pointer-events:none}
.orbit::after{content:"";position:absolute;width:7px;height:7px;right:17%;top:10%;background:var(--color-primary);border-radius:50%}

.auth-showcase .showcase-copy{padding-bottom:0}
.auth-showcase .showcase-copy p{max-width:330px}
.showcase-capabilities{margin-top:12px;padding-block:19px;position:relative}
.motion-toggle{position:absolute;z-index:3;right:12px;top:12px;width:44px;height:44px;display:grid;place-items:center;padding:8px;border:1px solid var(--color-border);border-radius:8px;color:var(--color-muted);background:var(--color-panel)}
.motion-toggle svg{width:16px;height:16px}
.motion-toggle:hover{color:var(--color-primary)}

@media(prefers-reduced-motion:no-preference) and (min-width:801px){
.art{animation:picture-float 8s ease-in-out infinite}
.copy-sample{animation:copy-float 8s ease-in-out infinite}
.video-sample{animation:video-float 8s ease-in-out infinite}
.sample-text{animation:write-copy 8s cubic-bezier(.16,1,.3,1) infinite}
.video-frames i{animation:frame-rhythm 2s ease-in-out infinite}
.video-frames i:nth-child(2n){animation-delay:-.5s}
.video-frames i:nth-child(3n){animation-delay:-1s}

@keyframes picture-float{0%,100%{transform:translateY(4px) rotate(-4deg)}
50%{transform:translateY(-10px) rotate(-2deg)}
}

@keyframes copy-float{0%,100%{transform:translateY(-4px) rotate(3deg)}
50%{transform:translateY(8px) rotate(1deg)}
}

@keyframes video-float{0%,100%{transform:translateY(7px) rotate(5deg)}
50%{transform:translateY(-9px) rotate(2deg)}
}

@keyframes write-copy{0%,12%{clip-path:inset(0 100% 0 0)}
45%,90%{clip-path:inset(0)}
100%{clip-path:inset(0 100% 0 0)}
}

@keyframes frame-rhythm{0%,100%{transform:scaleY(.5);opacity:.45}
50%{transform:scaleY(1);opacity:1}
}

}

.auth-showcase[data-paused=true] *{animation-play-state:paused!important}
.auth-showcase[data-paused=true] .stage-depth{transform:none}

@media(prefers-reduced-motion:reduce){.stage-depth{transform:none;transition:none}
.motion-toggle{display:none}
}

@media(min-width:801px) and (max-width:1100px){.art{inset-inline:32px}
.copy-sample{left:12px;width:220px;padding:13px 15px}
.sample-text{font-size:17px}
.video-sample{right:10px;padding:10px 12px}
.creative-stage{min-height:320px}
}

.auth-showcase { --auth-scene:color-mix(in srgb,var(--color-selected) 85%,var(--color-panel)); isolation:isolate; }

.sample-text { color:var(--color-text); }

.showcase-brand { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:16px; height:100%; padding:48px 24px; color:var(--color-primary); font-size:28px; font-weight:650; }

.showcase-brand span { overflow-wrap:anywhere; min-width:0; }

.showcase-brand :deep(img) { width:80px; height:80px; }

@media(min-height:880px) and (min-width:801px) { .showcase-copy { padding-top:42px; }
 }

@media(max-width:1100px) { .showcase-copy { padding-inline:28px; }
 .showcase-copy h2 { font-size:36px; }
 .showcase-capabilities { padding-inline:22px; gap:6px; }
 .showcase-capabilities span { gap:5px; font-size:11px; }
 }

@media(max-width:800px) { .auth-showcase { display:none; }
 }

</style>
