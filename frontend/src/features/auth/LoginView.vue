<script setup lang="ts">
import AuthForm from './AuthForm.vue'
import { useRoute } from 'vue-router'
const route = useRoute()
</script>
<template><AuthForm><template #notice><p v-if="route.query.passwordChanged === '1'" role="status" class="password-changed">密码已修改，请使用新密码重新登录。</p></template></AuthForm></template>
<style scoped>
.password-changed { margin:0 0 20px; padding:12px 16px; background:var(--color-success-bg); color:var(--color-success); border-radius:8px; font-size:14px; }
</style>
