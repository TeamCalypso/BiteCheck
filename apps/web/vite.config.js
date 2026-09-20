import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/v1': {
        target: process.env.VITE_API_BASE_URL || 'https://5607b13rz9.execute-api.us-east-1.amazonaws.com/prod',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
