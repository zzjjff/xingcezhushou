import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 通过代理把 /api 转发到后端 8000，前端直接请求 /api 即可，避开跨域
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
