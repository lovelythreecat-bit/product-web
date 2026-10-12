import { createRouter, createWebHistory } from 'vue-router'
import PlaceholderView from './views/PlaceholderView.vue'
import LoginView from './features/auth/LoginView.vue'
import RegisterView from './features/auth/RegisterView.vue'
import AccountView from './features/account/AccountView.vue'
import RechargeInfoView from './features/account/RechargeInfoView.vue'
import WorkspaceView from './features/workspace/WorkspaceView.vue'
import WorksView from './features/works/WorksView.vue'
import UsersView from './features/admin/UsersView.vue'
import AgentsView from './features/admin/AgentsView.vue'
import PricesView from './features/admin/PricesView.vue'
import TasksView from './features/admin/TasksView.vue'
import AuditView from './features/admin/AuditView.vue'
import { session, onIdentityChange } from './features/auth/session'
export const router = createRouter({ history:createWebHistory(), routes:[
  {path:'/',redirect:'/workspace'},
  {path:'/login',component:LoginView,meta:{public:true}},
  {path:'/register',component:RegisterView,meta:{public:true}},
  {path:'/account',component:AccountView},
  {path:'/recharge',component:RechargeInfoView},
  {path:'/workspace/:conversationId?',component:WorkspaceView},
  {path:'/works',component:WorksView},
  {path:'/admin',redirect:'/admin/users',meta:{admin:true}},
  {path:'/admin/users',component:UsersView,meta:{admin:true}},
  {path:'/admin/agents',component:AgentsView,meta:{admin:true}},
  {path:'/admin/prices',component:PricesView,meta:{admin:true}},
  {path:'/admin/tasks',component:TasksView,meta:{admin:true}},
  {path:'/admin/audit',component:AuditView,meta:{admin:true}},
  {path:'/:pathMatch(.*)*',component:PlaceholderView,meta:{title:'页面未找到'}}
] })
router.beforeEach(async to => {
  await session.restore()
  if (!to.meta.public && !session.profile.value) return '/login'
  if (to.meta.admin && session.profile.value?.role !== 'admin') return '/workspace'
  if (to.meta.public && session.profile.value) return '/workspace'
})
onIdentityChange(change => {
  if (!change.userId && router.currentRoute.value.matched.length && !router.currentRoute.value.meta.public) void router.replace('/login')
})
