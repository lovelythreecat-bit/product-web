<script setup lang="ts">
import { computed } from 'vue'
import artwork from '../../../assets/customer-service/approved-artwork.png'

// Display only illustration regions of the approved comp. Page copy remains HTML.
const props = defineProps<{ kind: 'book' | 'portrait' | 'horse' | 'avatar' }>()
const crop = computed(() => ({
  book: { x: 137, y: 857, width: 375, height: 105 },
  portrait: { x: 68, y: 1267, width: 267, height: 251 },
  horse: { x: 712, y: 1255, width: 308, height: 259 },
  avatar: { x: 517, y: 496, width: 44, height: 44 },
}[props.kind]))
const imageStyle = computed(() => ({
  width: `${1024 / crop.value.width * 100}%`,
  maxWidth: 'none',
  left: `${-crop.value.x / crop.value.width * 100}%`,
  top: `${-crop.value.y / crop.value.height * 100}%`,
}))
</script>

<template><span class="fairy-artwork" :class="`fairy-artwork--${kind}`" :style="{ aspectRatio: `${crop.width} / ${crop.height}` }" aria-hidden="true"><img :src="artwork" alt="" :style="imageStyle" width="1024" height="1536" loading="lazy" /></span></template>

<style scoped>
.fairy-artwork { display:block; position:relative; overflow:hidden; pointer-events:none; }
.fairy-artwork img { position:absolute; height:auto; }
.fairy-artwork--avatar { border-radius:50%; }
.fairy-artwork:not(.fairy-artwork--avatar) { mask-image:linear-gradient(to right,transparent,#000 12%,#000 88%,transparent),linear-gradient(to bottom,transparent,#000 12%,#000 86%,transparent); mask-composite:intersect; }
</style>
