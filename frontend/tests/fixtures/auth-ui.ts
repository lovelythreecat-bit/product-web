// Local visual fixture: real views and controls, no real identity or account writes.
import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import AppShell from '../../src/components/AppShell.vue'
import LoginView from '../../src/features/auth/LoginView.vue'
import RegisterView from '../../src/features/auth/RegisterView.vue'
import '../../src/styles/element-components'
import '../../src/styles/tokens.css'
import '../../src/styles/element-theme.css'

window.fetch = async () => {
  await new Promise(resolve => setTimeout(resolve, 1200))
  return new Response(JSON.stringify({ detail: 'TEST_ONLY unavailable' }), { status:503, headers:{'Content-Type':'application/json'} })
}
const router = createRouter({ history:createWebHashHistory(), routes:[
  {path:'/',redirect:'/login'},
  {path:'/login',component:LoginView},
  {path:'/register',component:RegisterView},
] })
createApp(AppShell).use(router).mount('#app')
