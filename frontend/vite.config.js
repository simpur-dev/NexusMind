import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const BACKEND_ORIGIN = 'http://localhost:5001'

export default defineConfig(() => ({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: false,
    open: true,
    proxy: {
      '/api': {
        target: BACKEND_ORIGIN,
        changeOrigin: true,
        secure: false
      }
    }
  }
}))
