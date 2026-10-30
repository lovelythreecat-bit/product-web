import { computed, ref } from 'vue'

export type Theme = 'light' | 'dark'
const key = 'yingzuo-theme'
export const theme = ref<Theme>('light')
function apply(value: Theme) {
  theme.value = value
  document.documentElement.dataset.theme = value
}
export function setTheme(value: Theme) {
  apply(value)
  try { localStorage.setItem(key, value) } catch { /* Theme still works without storage. */ }
}
export function initializeTheme() {
  try { apply(localStorage.getItem(key) === 'dark' ? 'dark' : 'light') } catch { apply('light') }
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) apply(event.newValue === 'dark' ? 'dark' : 'light')
  })
}

// ECharts paints SVG/canvas outside CSS; keep it in sync with the same palette.
export const chartColors = computed(() => theme.value === 'dark'
  ? { primary:'#79aaff', muted:'#a4b5ce', text:'#eaf1ff', panel:'#121e32', border:'#2b3d58', line:'#24344d', secondary:'#6fd4c5' }
  : { primary:'#1559d6', muted:'#586b85', text:'#182843', panel:'#ffffff', border:'#dbe3ef', line:'#e7edf5', secondary:'#137c83' })
