<script setup lang="ts">
withDefaults(defineProps<{ kind: 'fashion' | 'beauty' | 'digital'; decorative?: boolean }>(), { decorative: true })
const descriptions = { fashion: '奶油色运动鞋与卫衣创作示例', beauty: '琥珀色护肤瓶创作示例', digital: '黑色耳机创作示例' }
</script>
<template><div class="home-product-visual" :class="`home-product-visual--${kind}`"><img :src="'/homepage/commerce-categories-v3.png'" :alt="decorative ? '' : descriptions[kind]" width="2172" height="724" loading="lazy"/></div></template>
