<script setup lang="ts">
import { computed, normalizeClass, ref, useAttrs } from 'vue'
import { ElButton } from 'element-plus/es/components/button/index'
defineOptions({ inheritAttrs: false })
const props = withDefaults(defineProps<{ type?: 'button' | 'submit' | 'reset' }>(), { type: 'submit' })
const attrs = useAttrs()
const button = ref<InstanceType<typeof ElButton>>()
const appearance = computed(() => {
  const classes = normalizeClass(attrs.class).split(/\s+/)
  return classes.includes('danger') ? 'danger' : classes.includes('primary') ? 'primary' : 'default'
})
function focus() { (button.value?.$el as HTMLButtonElement | undefined)?.focus() }
function click() { (button.value?.$el as HTMLButtonElement | undefined)?.click() }
defineExpose({ focus, click })
</script>
<template><ElButton ref="button" v-bind="attrs" :native-type="props.type" :type="appearance" class="ui-button"><slot /></ElButton></template>
