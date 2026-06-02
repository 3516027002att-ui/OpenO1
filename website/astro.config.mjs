import { defineConfig } from 'astro/config';

const site = process.env.SITE_URL || 'https://3516027002att-ui.github.io';
const base = process.env.SITE_BASE || '/OpenO1';

export default defineConfig({
  site,
  base,
  markdown: {
    shikiConfig: {
      theme: 'github-light'
    }
  }
});
