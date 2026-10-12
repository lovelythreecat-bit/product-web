<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { session } from './session'
import { ApiError } from '../../api/client'
import type { Schema } from '../../types/api'
const props = defineProps<{ register?: boolean }>()
const router = useRouter()
const account = ref(''), password = ref(''), error = ref('')
const accountError = ref(''), passwordError = ref('')
let intent: Readonly<Schema<'RegisterRequest'>> | undefined
function edited() { intent = undefined; error.value = '' }
onBeforeUnmount(() => { password.value = ''; intent = undefined })
async function submit() {
  if (session.busy.value) return
  accountError.value = [...account.value].length < 3 || [...account.value].length > 64 ? '账号需要 3–64 个字符。' : ''
  passwordError.value = [...password.value].length < 10 || [...password.value].length > 128 ? '密码需要 10–128 个字符。' : ''
  if (accountError.value || passwordError.value) return
  error.value = ''
  if (props.register && !intent) intent = Object.freeze({ account: account.value, password: password.value, request_key: crypto.randomUUID() })
  try {
    if (await session.authenticate(intent ?? { account: account.value, password: password.value })) {
      password.value = ''; intent = undefined
      await router.replace('/workspace')
    }
  } catch (e) {
    // Never surface server validation details, request bodies or credentials.
    error.value = e instanceof ApiError && e.status === 0 ? '网络连接失败，请重试。同一次注册重试会沿用原请求。' : props.register ? '注册未完成，请检查账号是否已使用，或稍后重试。' : '登录未完成，请检查账号和密码，或稍后重试。'
  }
}
</script>
<template>
  <section class="auth-card panel">
    <p class="eyebrow">电商 AI 创作平台</p>
    <h1>{{ register ? '创建账号' : '登录' }}</h1>
    <p>{{ register ? '使用账号和密码开始创作。' : '登录后继续管理你的创作与积分。' }}</p>
    <form class="form-stack" @submit.prevent="submit" novalidate>
      <div><label for="auth-account">账号</label><input id="auth-account" v-model="account" :disabled="session.busy.value" autocomplete="username" aria-describedby="account-help account-error" @input="edited"><small id="account-help">3–64 个字符</small><p id="account-error" class="field-error" role="alert">{{ accountError }}</p></div>
      <div><label for="auth-password">密码</label><input id="auth-password" v-model="password" :disabled="session.busy.value" type="password" :autocomplete="register ? 'new-password' : 'current-password'" aria-describedby="password-help password-error" @input="edited"><small id="password-help">10–128 个字符</small><p id="password-error" class="field-error" role="alert">{{ passwordError }}</p></div>
      <p v-if="error || session.error.value" class="field-error" role="alert">{{ error || session.error.value }}</p>
      <button type="submit" class="button primary" :disabled="session.busy.value">{{ session.busy.value ? '正在提交…' : register ? '创建账号' : '登录' }}</button>
    </form>
    <p class="auth-switch"><RouterLink :to="register ? '/login' : '/register'">{{ register ? '已有账号？前往登录' : '还没有账号？创建账号' }}</RouterLink></p>
  </section>
</template>
