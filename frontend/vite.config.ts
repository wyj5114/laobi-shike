import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  base: './',
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3017,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:8484',
        changeOrigin: true,
      },
      '/media': {
        target: process.env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:8484',
        changeOrigin: true,
      },
      '/static': {
        target: process.env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:8484',
        changeOrigin: true,
      },
      '/uploads': {
        target: process.env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:8484',
        changeOrigin: true,
      },
    },
  },
})
