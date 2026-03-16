import { defineConfig } from 'vite';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: '.',
  publicDir: 'public',
  build: {
    outDir: 'dist',
    assetsDir: 'assets-bundled',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        kindworth: resolve(__dirname, 'kindworth.html'),
      },
    },
  },
  server: {
    port: 5199,
    open: false,
    host: true,
  },
});
