import { onBeforeUnmount, ref } from 'vue'
import './admin.css'
import { ApiError } from '../../api/client'
import { session } from '../auth/session'
export function useAdminRequest() {
  const busy = ref(false), error = ref('')
  const epoch = session.epoch.value
  let active = true
  const current = () => active && epoch === session.epoch.value
  onBeforeUnmount(() => { active = false })
  async function run<T>(task: () => Promise<T>, apply: (result:T) => void): Promise<boolean> {
    if (busy.value || !current()) return false
    busy.value = true; error.value = ''
    try { const result = await task(); if (!current()) return false; apply(result); return true }
    catch (e) { if (current()) error.value = e instanceof ApiError ? (e.status === 409 ? '数据已更新或操作冲突，草稿已保留。请关闭后重新打开编辑。' : e.message) : e instanceof Error ? e.message : '操作未完成，草稿已保留。'; return false }
    finally { if (current()) busy.value = false }
  }
  return { busy, error, current, run }
}
export const date = (value: string) => new Date(value).toLocaleString('zh-CN')
export const pretty = (value: unknown) => JSON.stringify(value, null, 2)
export const taskStates: Record<string,string> = {SUBMITTED:'已提交',QUEUED:'排队中',SUBMITTING:'提交上游中',RUNNING:'执行中',INVESTIGATING:'待核查',SAVING:'结果保存中',SAVE_RECOVERY:'保存失败待恢复',SUCCEEDED:'成功',FAILED:'失败',MANUALLY_CLOSED:'人工关闭'}
export const settlements: Record<string,string> = {FROZEN:'冻结中',CONSUMED:'已消费',RELEASED:'已释放'}
