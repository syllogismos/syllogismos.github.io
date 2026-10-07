import { defineConfig } from 'astro/config';
import { createCssVariablesTheme } from 'shiki/core';

// Token colours come from the --code-* custom properties in src/styles/global.css.
const inkTheme = createCssVariablesTheme({
  name: 'ink',
  variablePrefix: '--code-',
  fontStyle: true,
});

export default defineConfig({
  site: 'https://syllogismos.github.io',
  trailingSlash: 'always',
  redirects: {
    // The home page lists every post, so the old second page points back to it.
    '/posts/2': '/',
  },
  markdown: {
    shikiConfig: { theme: inkTheme },
  },
});
