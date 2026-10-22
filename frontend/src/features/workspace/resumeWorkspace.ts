import { getTask, listTasks } from '../../api/tasks'

/** Resolve a durable original; entering the workspace never submits a task. */
export async function resumeWorkspace(): Promise<string | undefined> {
  try {
    const page = await listTasks(undefined, undefined, undefined, 'ordinary')
    const latest = page.items[0]
    if (!latest) return
    const detail = await getTask(latest.task_id)
    if (detail.conversation_id) return '/workspace/' + encodeURIComponent(detail.conversation_id)
  } catch { /* Keep navigation available; history can be reopened from the sidebar. */ }
}
