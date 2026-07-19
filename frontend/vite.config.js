import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      // Mirrors the nginx reverse-proxy shape used in deployment, so
      // frontend code can call /api/... the same way in dev and prod.
      '/api': 'http://localhost:8000',
    },
  },
})
