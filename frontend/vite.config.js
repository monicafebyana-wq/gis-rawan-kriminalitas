import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev server: http://localhost:5173
export default defineConfig({
  plugins: [react()],
});
