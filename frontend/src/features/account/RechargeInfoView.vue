<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { session } from '../auth/session'
const error = ref(''), loading = ref(false)
async function load() { loading.value = true; error.value = ''; try { await session.refreshAccount() } catch { error.value = '当前积分暂时无法读取，请重试。' } finally { loading.value = false } }
onMounted(load)
</script>
<template><section class="page-heading"><p class="eyebrow">积分服务</p><h1>充值说明</h1><p>首版尚未开通真实充值</p></section><section class="panel recharge-panel"><h2>当前积分</h2><div v-if="session.account.value" class="balance-grid"><div><span>可用积分</span><strong>{{ session.account.value.available }}</strong></div><div><span>冻结积分</span><strong>{{ session.account.value.frozen }}</strong></div><div><span>已消费积分</span><strong>{{ session.account.value.consumed }}</strong></div></div><p v-if="loading" role="status">正在读取积分…</p><p v-if="error" role="alert" class="field-error">{{ error }}</p><button v-if="error" type="button" class="button" @click="load">重新读取</button><p>在线充值暂未开放。微信、支付宝支付将在后续版本接入，当前不会创建支付订单或扣款。</p><p>试用及发放积分以账户实际记录为准。</p><RouterLink class="button" to="/account">查看积分流水</RouterLink></section></template>
