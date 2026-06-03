import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/react/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://localhost:6001',
        secure: false,
        changeOrigin: true,
      },
      '/strategies/api': {
        target: 'https://localhost:6001',
        secure: false,
        changeOrigin: true,
      },
      '/orders/api': {
        target: 'https://localhost:6001',
        secure: false,
        changeOrigin: true,
      },
    },
  },
})
