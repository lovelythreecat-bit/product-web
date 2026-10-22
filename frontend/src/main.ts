import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import './styles/element-components'
import './styles/tokens.css'
import './styles/element-theme.css'
import './features/workspace/workspace.css'
createApp(App).use(router).mount('#app')
