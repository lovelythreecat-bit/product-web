<script setup lang="ts">
import UiInput from '../../components/ui/UiInput.vue'
import UiButton from '../../components/ui/UiButton.vue'
import { onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppDrawer from '../../components/AppDrawer.vue'
import { ApiError } from '../../api/client'
import { session } from '../auth/session'
const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [open: boolean] }>()
const router = useRouter()
const current = ref(''), password = ref(''), confirmation = ref('')
const currentError = ref(''), passwordError = ref(''), confirmationError = ref(''), error = ref(''), saving = ref(false)
let alive = true
function clear() { current.value = ''; password.value = ''; confirmation.value = ''; currentError.value = ''; passwordError.value = ''; confirmationError.value = ''; error.value = '' }
watch(() => props.open, clear)
watch(session.epoch, () => { clear(); emit('update:open', false) })
onBeforeUnmount(() => { alive = false; clear() })
async function save() {
  if (saving.value) return
  currentError.value = !current.value ? '请输入当前密码。' : ''
  passwordError.value = [...password.value].length < 10 || [...password.value].length > 128 ? '新密码需要 10–128 个字符。' : password.value === current.value ? '新密码不能与当前密码相同。' : ''
  confirmationError.value = password.value !== confirmation.value ? '两次密码不一致，请重新确认。' : ''
  if (currentError.value || passwordError.value || confirmationError.value) return
  saving.value = true; error.value = ''
  const version = session.epoch.value
  try {
    if (await session.changePassword({ current_password: current.value, new_password: password.value })) {
      clear(); emit('update:open', false)
      await router.replace({ path: '/login', query: { passwordChanged: '1' } })
    }
  } catch (e) {
    if (alive && props.open && version === session.epoch.value) {
      if (e instanceof ApiError && e.status === 400) currentError.value = '当前密码不正确，请重新输入。'
      else error.value = e instanceof ApiError ? e.message : '修改未完成，请重试。'
    }
  }
  finally { saving.value = false }
}
</script>
<template>
  <AppDrawer :open="open" title="修改密码" purpose="edit" @update:open="emit('update:open', $event)">
    <form id="password-change-form" class="form-stack" novalidate @submit.prevent="save">
      <p class="field-hint">修改成功后，所有已登录设备需要使用新密码重新登录。</p>
      <div><label for="current-password">当前密码</label><UiInput id="current-password" v-model="current" data-initial-focus type="password" autocomplete="current-password" :disabled="saving" :aria-invalid="!!currentError" aria-describedby="current-password-error" /><p id="current-password-error" class="field-error" role="alert">{{ currentError }}</p></div>
      <div><label for="new-password">新密码</label><UiInput id="new-password" v-model="password" type="password" autocomplete="new-password" :disabled="saving" :aria-invalid="!!passwordError" aria-describedby="new-password-help new-password-error" /><small id="new-password-help">10–128 个字符</small><p id="new-password-error" class="field-error" role="alert">{{ passwordError }}</p></div>
      <div><label for="confirm-password">确认新密码</label><UiInput id="confirm-password" v-model="confirmation" type="password" autocomplete="new-password" :disabled="saving" :aria-invalid="!!confirmationError" aria-describedby="confirm-password-error" /><p id="confirm-password-error" class="field-error" role="alert">{{ confirmationError }}</p></div>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
    </form>
    <template #actions><UiButton type="submit" form="password-change-form" class="button primary" :disabled="saving">{{ saving ? '正在修改…' : '确认修改' }}</UiButton></template>
  </AppDrawer>
</template>
