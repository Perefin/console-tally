import { defineConfig } from 'astro/config';

// Deployed at https://perefin.github.io/console-tally/
export default defineConfig({
  site: 'https://perefin.github.io',
  base: '/console-tally',
  trailingSlash: 'ignore',
  build: {
    format: 'directory',
  },
});
