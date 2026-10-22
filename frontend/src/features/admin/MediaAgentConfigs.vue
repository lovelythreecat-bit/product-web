<script setup lang="ts">
import ImageAgentConfigs from './ImageAgentConfigs.vue'
import VideoAgentConfigs from './VideoAgentConfigs.vue'
import type { MediaKind } from '../../api/mediaAgents'
defineProps<{ kind: MediaKind }>()
</script>

<template>
  <ImageAgentConfigs v-if="kind==='image'" />
  <VideoAgentConfigs v-else />
</template>
