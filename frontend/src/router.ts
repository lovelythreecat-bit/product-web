import { createRouter, createWebHistory } from 'vue-router'
import PlaceholderView from './views/PlaceholderView.vue'
export const router = createRouter({ history:createWebHistory(), routes:[
  {path:'/',redirect:'/workspace'},
  ...[['/login','登录'],['/register','注册'],['/workspace/:conversationId?','创作工作台'],['/works','我的作品'],['/account','个人中心'],['/recharge','充值说明']].map(([path,title]) => ({path,component:PlaceholderView,meta:{title}})),
  {path:'/:pathMatch(.*)*',component:PlaceholderView,meta:{title:'页面未找到'}}
] })
