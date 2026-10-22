import { createRouter, createWebHistory } from 'vue-router'
import PlaceholderView from './views/PlaceholderView.vue'
import LoginView from './features/auth/LoginView.vue'
import RegisterView from './features/auth/RegisterView.vue'
import AccountView from './features/account/AccountView.vue'
import RechargeInfoView from './features/account/RechargeInfoView.vue'
import WorkspaceView from './features/workspace/WorkspaceView.vue'
import QuickGenerationView from './features/quick-generation/QuickGenerationView.vue'
import WorksView from './features/works/WorksView.vue'
import UsersView from './features/admin/UsersView.vue'
import AgentsView from './features/admin/AgentsView.vue'
import CreditsView from './features/admin/CreditsView.vue'
import ParametersView from './features/admin/ParametersView.vue'
import TasksView from './features/admin/TasksView.vue'
import HomeView from './features/site/HomeView.vue'
import AuditView from './features/admin/AuditView.vue'
import { session, onIdentityChange } from './features/auth/session'
import { resumeWorkspace } from './features/workspace/resumeWorkspace'
export const router = createRouter({ history:createWebHistory(), routes:[
  {path:'/',component:HomeView,meta:{public:true}},
  {path:'/login',component:LoginView,meta:{public:true}},
  {path:'/register',component:RegisterView,meta:{public:true}},
  {path:'/account',component:AccountView},
  {path:'/recharge',component:RechargeInfoView},
  {path:'/workspace',redirect:'/workspace/quick'},
  {path:'/workspace/quick/:runId?',component:QuickGenerationView},
  {path:'/workspace/ordinary',component:WorkspaceView},
  {path:'/workspace/:conversationId',component:WorkspaceView},
  {path:'/works',component:WorksView},
  {path:'/admin',redirect:'/admin/tasks',meta:{admin:true}},
  {path:'/admin/users',component:UsersView,meta:{admin:true}},
  {path:'/admin/credits',component:CreditsView,meta:{admin:true}},
  {path:'/admin/agents',component:AgentsView,meta:{admin:true}},
  {path:'/admin/parameters',component:ParametersView,meta:{admin:true}},
  {path:'/admin/specs',redirect:'/admin/parameters',meta:{admin:true}},
  {path:'/admin/prices',redirect:'/admin/parameters',meta:{admin:true}},
  {path:'/admin/tasks',component:TasksView,meta:{admin:true}},
  {path:'/admin/usage',component:() => import('./features/admin/UsageView.vue'),meta:{admin:true}},
  {path:'/admin/logs',component:AuditView,meta:{admin:true}},
  {path:'/admin/audit',redirect:'/admin/logs',meta:{admin:true}},
  {path:'/:pathMatch(.*)*',component:PlaceholderView,meta:{title:'页面未找到'}}
] })
router.beforeEach(async to => {
  await session.restore()
  if (!to.meta.public && !session.profile.value) return '/login'
  if (to.meta.admin && session.profile.value?.role !== 'admin') return '/workspace'
  if (['/login','/register'].includes(to.path) && session.profile.value) return '/workspace'
  if (to.path === '/workspace/ordinary' || to.path === '/workspace/ordinary/') {
    const epoch = session.epoch.value
    const original = await resumeWorkspace()
    if (!session.profile.value) return '/login'
    if (epoch === session.epoch.value && original) return { path: original, replace: true }
  }
})
onIdentityChange(change => {
  if (!change.userId && router.currentRoute.value.matched.length && !router.currentRoute.value.meta.public) void router.replace('/login')
})
