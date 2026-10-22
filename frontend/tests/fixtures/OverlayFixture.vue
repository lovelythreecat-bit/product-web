<script setup lang="ts">
import { ref } from 'vue'
import AppDialog from '../../src/components/AppDialog.vue'
import AppDrawer from '../../src/components/AppDrawer.vue'
const formOpen=ref(false), formSubmits=ref(0)
const formPurpose=ref<'read'|'edit'|'charge'|'delete'>('edit')
const formVariant=ref<'dialog'|'drawer'>('dialog')
const charge=ref(false),detail=ref(false),edit=ref(false),preview=ref(false),remove=ref(false)
</script>
<template><main><h1>TEST_ONLY 共享弹层验收</h1><button class="button" @click="charge=true">打开收费确认</button><button class="button" @click="detail=true">打开详情</button><button class="button" @click="edit=true">编辑资料</button><button class="button" @click="preview=true">预览</button><button class="button" @click="remove=true">删除确认</button><AppDialog v-model:open="remove" title="删除作品" purpose="delete"><p>仅测试删除确认焦点。</p><template #actions><button class="button danger" @click="remove=false">删除</button></template></AppDialog><AppDialog v-model:open="charge" title="确认本次费用" purpose="charge"><p>仅组件测试，不提交业务任务。</p><template #actions><button class="button primary" @click="charge=false">确认</button></template></AppDialog><AppDrawer v-model:open="detail" title="任务详情"><p v-for="n in 40" :key="n">只读详情 {{n}}。长内容仅滚动内容区域。</p></AppDrawer><AppDrawer v-model:open="edit" title="编辑商品资料" purpose="edit"><label for="product">商品名称</label><input id="product" data-initial-focus value="测试资料"/><template #actions><button class="button primary" @click="edit=false">保存</button></template></AppDrawer><AppDialog v-model:open="preview" title="作品预览"><p>只读预览。</p></AppDialog><form id="parent-overlay-form" @submit.prevent="formSubmits++">
<label>组合类型<select v-model="formVariant"><option value="dialog">dialog</option><option value="drawer">drawer</option></select></label>
<label>组合用途<select v-model="formPurpose"><option value="read">read</option><option value="edit">edit</option><option value="charge">charge</option><option value="delete">delete</option></select></label>
<button type="button" class="button" @click="formOpen=true">打开父表单弹层</button>
<output data-testid="form-submits">{{ formSubmits }}</output><output data-testid="form-open">{{ formOpen }}</output>
<component :is="formVariant === 'dialog' ? AppDialog : AppDrawer" v-model:open="formOpen" title="父表单组合" :purpose="formPurpose">
<p>TEST_ONLY：取消或关闭不能提交父表单。</p>
<template #actions><button type="submit" form="parent-overlay-form" class="button primary">明确提交</button></template>
</component></form></main></template>
