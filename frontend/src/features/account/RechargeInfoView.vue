<script setup lang="ts">
import UiButton from '../../components/ui/UiButton.vue'
import { onMounted, ref } from 'vue'
import { session } from '../auth/session'
import AppIcon from '../../components/AppIcon.vue'
const error = ref(''), loading = ref(false)
async function load() { loading.value = true; error.value = ''; try { await session.refreshAccount() } catch { error.value = '当前积分暂时无法读取，请重试。' } finally { loading.value = false } }
onMounted(load)
</script>
<template>
  <section class="panel recharge-panel" aria-label="充值积分">
    <p>当前可用积分</p>
    <div v-if="session.account.value" class="recharge-balance"><strong>{{ session.account.value.available }}</strong><span>冻结 {{ session.account.value.frozen }}</span></div>
    <p v-if="loading" role="status">正在读取积分…</p><p v-if="error" role="alert" class="field-error">{{ error }}</p><UiButton v-if="error" type="button" class="button" :disabled="loading" @click="load">重新读取</UiButton>
    <p class="recharge-notice"><AppIcon name="info" />在线充值暂未开放</p>
    <p class="recharge-explanation"><strong>首版使用注册赠送与管理员发放的试用积分。</strong><span>后续计划接入微信、支付宝；兑换比例、档位和退款规则将在支付阶段确认。</span></p>
    <p class="recharge-boundary"><AppIcon name="info" />此页面不会创建订单、调用支付渠道或增加积分。</p>
    <RouterLink class="button primary" to="/workspace">返回创作工作台</RouterLink>
  </section>
</template>
<style scoped>
.recharge-panel { max-width:840px; margin:16px auto; padding:24px; }
.recharge-balance { display:flex; align-items:baseline; flex-wrap:wrap; gap:16px; margin:8px 0 16px; font-variant-numeric:tabular-nums; }
.recharge-balance strong { font-size:64px; line-height:1.2; color:var(--color-primary); overflow-wrap:anywhere; }
.recharge-balance span { color:var(--color-muted); padding-left:20px; border-left:1px solid var(--color-border); }
.recharge-notice { display:flex; align-items:center; gap:16px; background:var(--color-message); color:var(--color-text); border:1px solid var(--color-border); border-radius:10px; padding:16px; font-weight:600; font-size:18px; }
.recharge-notice svg { width:28px; height:28px; color:var(--color-primary); flex-shrink:0; }
.recharge-explanation { margin:16px 0; line-height:1.8; }
.recharge-explanation strong,.recharge-explanation span { display:block; }
.recharge-explanation span { margin-top:10px; color:var(--color-muted); }
.recharge-boundary { display:flex; align-items:flex-start; gap:12px; font-size:14px; padding-top:16px; border-top:1px solid var(--color-border); }
.recharge-boundary svg { width:20px; height:20px; flex-shrink:0; margin-top:2px; }
.recharge-panel>.button.primary { display:flex; width:max-content; max-width:100%; min-width:240px; margin:16px auto 0; }
@media(max-width:700px) { .recharge-panel { padding:20px 16px; margin:8px auto; } .recharge-balance strong { font-size:48px; } .recharge-notice { font-size:16px; padding:12px; } .recharge-panel>.button.primary { width:100%; min-width:0; } }
</style>
