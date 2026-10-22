<script setup lang="ts">
import UiButton from '../../components/ui/UiButton.vue'
import { ref } from 'vue'
import TextModelConfigs from './TextModelConfigs.vue'
import TextServiceConnection from './TextServiceConnection.vue'
import MediaAgentConfigs from './MediaAgentConfigs.vue'
const selectedKind=ref<'copy'|'image'|'video'>('copy'), connectionVersion=ref(0), notice=ref('')
</script>
<template>
 <div class="admin-page"><header class="page-heading admin-heading-with-action">
 <div class="agent-kind-switch" role="group" aria-label="配置类型"><UiButton v-for="item in [{kind:'copy',name:'文本'},{kind:'image',name:'图片'},{kind:'video',name:'视频'}] as const" :key="item.kind" class="button" :class="{primary:selectedKind===item.kind}" :aria-pressed="selectedKind===item.kind" @click="selectedKind=item.kind">{{ item.name }}</UiButton></div>
 <UiButton class="button" @click="connectionVersion++">刷新当前版本</UiButton></header><p v-if="notice" role="status">{{ notice }}</p>
 <TextServiceConnection v-if="selectedKind==='copy'" @saved="connectionVersion++" />
 <TextModelConfigs v-if="selectedKind==='copy'" :key="connectionVersion" @default-saved="notice='默认文本模型已更新。'" />
 <MediaAgentConfigs v-if="selectedKind!=='copy'" :key="selectedKind+':'+connectionVersion" :kind="selectedKind" /></div>
</template>
<style scoped>
.agent-kind-switch { display:flex; gap:4px; padding:4px; border:1px solid var(--color-border); border-radius:10px; background:var(--color-panel); }
.agent-kind-switch .button { margin:0; min-width:84px; border-color:transparent; background:transparent; color:var(--color-muted); }
.agent-kind-switch .button.primary { background:var(--color-selected); color:var(--color-primary); font-weight:600; }
.agent-kind-switch .button:hover { background:var(--color-background); }
.agent-kind-switch .button.primary:hover { background:var(--color-selected); }
@media(max-width:600px) { .agent-kind-switch { flex:1; } .agent-kind-switch .button { flex:1; min-width:0; } }
</style>
