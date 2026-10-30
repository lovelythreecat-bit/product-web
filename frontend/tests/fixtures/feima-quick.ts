// TEST_ONLY wrapper around the existing isolated quick-generation fixture.
import '../../src/styles/themes.css'
import { setTheme } from '../../src/styles/theme'
setTheme(new URLSearchParams(location.search).get('theme') === 'dark' ? 'dark' : 'light')
await import('./quick-ui')
const read = window.fetch
window.fetch = async (input, init) => String(input).includes('/api/v1/site/brand')
  ? new Response(JSON.stringify({name:'飞马',version:1}),{headers:{'Content-Type':'application/json'}})
  : read(input, init)
const { applyBrand } = await import('../../src/features/site/brand')
applyBrand({name:'飞马',version:1})
