import { createRouter, createWebHistory } from 'vue-router'
import PlaceholderView from './views/PlaceholderView.vue'
import LoginView from './features/auth/LoginView.vue'
import RegisterView from './features/auth/RegisterView.vue'
import AccountView from './features/account/AccountView.vue'
import RechargeInfoView from './features/account/RechargeInfoView.vue'
import { session, onIdentityChange } from './features/auth/session'
export const router = createRouter({ history:createWebHistory(), routes:[
  {path:'/',redirect:'/workspace'},
  {path:'/login',component:LoginView,meta:{public:true}},
  {path:'/register',component:RegisterView,meta:{public:true}},
  {path:'/account',component:AccountView},
  {path:'/recharge',component:RechargeInfoView},
  ...[['/workspace/:conversationId?','创作工作台'],['/works','我的作品']].map(([path,title]) => ({path,component:PlaceholderView,meta:{title}})),
  {path:'/:pathMatch(.*)*',component:PlaceholderView,meta:{title:'页面未找到'}}
] })
router.beforeEach(async to => {
  await session.restore()
  if (!to.meta.public && !session.profile.value) return '/login'
  if (to.meta.public && session.profile.value) return '/workspace'
})
onIdentityChange(change => {
  if (!change.userId && router.currentRoute.value.matched.length && !router.currentRoute.value.meta.public) void router.replace('/login')
})
