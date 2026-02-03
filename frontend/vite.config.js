import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// import path from 'path'

// // https://vite.dev/config/
// export default defineConfig({
//     plugins: [react()],
//
//     base: '/',
//
//     build: {
//         outDir: path.resolve(__dirname, '../app/static/dashboard'),
//         emptyOutDir: true,
//     },
// })



export default defineConfig({
    plugins: [react()],
    build: {
        outDir: 'dist',
        emptyOutDir: true
    }
})
