<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as api from '../../api/admin'
import type { Schema } from '../../types/api'
import AppDrawer from '../../components/AppDrawer.vue'
import { useAdminRequest, date, pretty } from './shared'
const {busy,error,run}=useAdminRequest()
const rows=ref<Schema<'AuditView'>[]>([]),cursor=ref<string|null>(null),action=ref(''),actor=ref(''),object=ref(''),open=ref(false),detail=ref<Schema<'AuditView'>|null>(null)
let applied={action:'',actor:'',object:''}
function load(reset=true){const filter=reset?{action:action.value,actor:actor.value,object:object.value}:applied;return run(()=>api.listAudit(reset?undefined:cursor.value??undefined,filter.action||undefined,filter.actor||undefined,filter.object||undefined),p=>{applied=filter;rows.value=reset?p.items:[...rows.value,...p.items];cursor.value=p.next_cursor})}
onMounted(load)
</script>
<template><div class="admin-page"><header class="page-heading"><h1>操作审计</h1><p>查询操作人、对象、原因及脱敏后的版本变更。</p></header><section class="panel"><form class="admin-filters" @submit.prevent="load()"><label>操作类型<input v-model="action" placeholder="留空查询全部"></label><label>操作人标识<input v-model="actor"></label><label>对象标识<input v-model="object"></label><button class="button" :disabled="busy">查询审计</button></form><p v-if="error" role="alert" class="field-error">{{ error }}</p><div class="admin-table"><table><thead><tr><th>时间</th><th>操作</th><th>操作人</th><th>对象</th><th>原因</th><th>详情</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td>{{ date(row.created_at) }}</td><td>{{ row.action }}</td><td>{{ row.actor_id || '系统' }}</td><td>{{ row.object_id }}</td><td>{{ row.reason }}</td><td><button class="button" @click="detail=row;open=true">查看详情</button></td></tr></tbody></table></div><p v-if="!busy && !rows.length">暂无匹配的审计记录。</p><button v-if="cursor" class="button" :disabled="busy" @click="load(false)">加载更多审计</button></section></div><AppDrawer v-model:open="open" title="操作审计详情"><template v-if="detail"><dl class="detail-list"><dt>操作人</dt><dd>{{ detail.actor_id || '系统' }}</dd><dt>对象</dt><dd>{{ detail.object_id }}</dd><dt>操作</dt><dd>{{ detail.action }}</dd><dt>原因</dt><dd>{{ detail.reason }}</dd><dt>时间</dt><dd>{{ date(detail.created_at) }}</dd></dl><h3>变更记录</h3><pre>{{ pretty(detail.changes) }}</pre></template></AppDrawer></template>
