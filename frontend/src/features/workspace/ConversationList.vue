<script setup lang="ts">
import { onScopeDispose, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createConversation, listConversations } from '../../api/conversations'
import type { Schema } from '../../types/api'
import { session } from '../auth/session'
const route = useRoute(), router = useRouter()
const items = ref<Schema<'ConversationSummary'>[]>([]), error = ref(''), busy = ref(false), cursor = ref<string>()
let revision = 0, alive = true
onScopeDispose(() => { alive = false; revision++ })
async function load(more = false) { const stamp = ++revision, epoch = session.epoch.value; try { const page = await listConversations(more ? cursor.value : undefined); if (!alive || stamp !== revision || epoch !== session.epoch.value) return; items.value = more ? [...items.value, ...page.items.filter(x => !items.value.some(y => y.conversation_id === x.conversation_id))] : page.items; cursor.value = page.next_cursor ?? undefined } catch { if (alive && stamp === revision) error.value = '会话暂时无法读取。' } }
async function create() { if (busy.value) return; busy.value = true; try { const item = await createConversation({ title: '新会话' }); await router.push('/workspace/' + item.conversation_id) } catch { error.value = '新会话创建失败，请重试。' } finally { busy.value = false } }
watch(() => route.fullPath, () => { if (!route.meta.public) void load() }, { immediate: true })
</script>
<template><div class="conversation-nav"><button class="button primary" type="button" :disabled="busy" @click="create">＋ 新建会话</button><label class="mobile-history" for="conversation-choice">历史会话</label><select id="conversation-choice" class="mobile-history" :value="route.params.conversationId || ''" @change="router.push('/workspace/' + ($event.target as HTMLSelectElement).value)"><option value="">选择历史会话</option><option v-for="item in items" :key="item.conversation_id" :value="item.conversation_id">{{ item.title }} · {{ item.conversation_id.slice(0, 8) }}</option></select><div class="desktop-history"><p>最近会话</p><RouterLink v-for="item in items" :key="item.conversation_id" :to="'/workspace/' + item.conversation_id">{{ item.title }}<small>{{ item.created_at.slice(0, 10) }} · {{ item.conversation_id.slice(0, 8) }}</small></RouterLink><p v-if="!items.length">从商品资料开始，创建第一份作品。</p></div><button v-if="cursor" class="button" type="button" @click="load(true)">更多会话</button><p v-if="error" role="alert">{{ error }}</p></div></template>
