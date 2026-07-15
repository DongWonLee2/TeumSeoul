import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // todo: 추후에 수정
        //rget: 'https://teumseoul-backend.onrender.com',
        changeOrigin: true,
        secure: true,
      },
    },
  },
})
