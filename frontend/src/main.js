import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

const installPlugins = (app) => {
  app.use(router)
  return app
}

installPlugins(createApp(App)).mount('#app')
