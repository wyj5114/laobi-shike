import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './design/tokens.css'
import { applyTheme, getStoredTheme } from './design/themes'

applyTheme(getStoredTheme())

createApp(App).use(createPinia()).use(router).mount('#app')
