<script setup lang="ts">
import { ref } from 'vue'
import UiInput from '../../src/components/ui/UiInput.vue'
import UiSelect from '../../src/components/ui/UiSelect.vue'
import UiButton from '../../src/components/ui/UiButton.vue'
import AppDrawer from '../../src/components/AppDrawer.vue'
import AppDialog from '../../src/components/AppDialog.vue'
const open = ref(false), charge = ref(false), pending = ref(false)
const name = ref(''), amount = ref<number | string>(''), enabled = ref<boolean | string>(''), custom = ref('')
const saved = ref('尚未保存')
function save() { saved.value = JSON.stringify({ name: name.value, amount: amount.value, enabled: enabled.value, custom: custom.value }); open.value = false }
</script>
<template>
  <main class="control-fixture"><h1>TEST_ONLY Element Plus 表单验证</h1>
    <UiButton type="button" class="button primary" @click="open = true">编辑测试资料</UiButton>
    <UiButton type="button" class="button" @click="charge = true">测试费用确认</UiButton>
    <output data-saved>{{ saved }}</output>
    <AppDrawer v-model:open="open" title="测试资料" purpose="edit">
      <UiButton type="button" class="button" @click="pending = !pending">{{ pending ? '解除冻结' : '模拟提交冻结' }}</UiButton>
      <form id="ui-native-form" class="form-stack" @submit.prevent="save">
        <fieldset :disabled="pending" class="form-stack">
          <div><label for="test-name">商品名称</label><UiInput id="test-name" v-model="name" required data-initial-focus /></div>
          <div><label for="test-amount">测试数量</label><UiInput id="test-amount" v-model.number="amount" type="number" min="1" step="1" required /></div>
          <div><label for="test-enabled">配置状态</label><UiSelect id="test-enabled" v-model="enabled" required><option value="" disabled>请选择状态</option><option :value="true">启用</option><option :value="false">停用</option></UiSelect></div>
          <div><label for="test-custom">可自定义要求</label><UiInput id="test-custom" v-model="custom" :suggestions="['自然', '专业', '亲切']" /></div>
        </fieldset>
      </form>
      <template #actions><UiButton class="button primary" form="ui-native-form" :disabled="pending">保存测试资料</UiButton></template>
    </AppDrawer>
    <AppDialog v-model:open="charge" title="测试费用确认" purpose="charge"><p>TEST_ONLY，不调用业务接口。</p><template #actions><UiButton type="button" class="button primary" @click="charge = false">确认测试费用</UiButton></template></AppDialog>
  </main>
</template>
<style scoped>.control-fixture { max-width:720px; margin:auto; padding:24px }.control-fixture>output { display:block; margin-top:24px; overflow-wrap:anywhere }fieldset { margin:16px 0 0; padding:0; border:0; min-width:0 }</style>
