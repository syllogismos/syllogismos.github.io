# syllogismos.github.io

Source for [syllogismos.github.io](https://syllogismos.github.io), built with [Astro](https://astro.build).

## Working on it

```sh
npm install
npm run dev      # local preview at http://localhost:4321
npm run build    # writes the static site to dist/
```

Pushing to `master` builds and publishes the site through GitHub Actions (`.github/workflows/deploy.yml`).

## Writing a post

Add a Markdown file to `src/content/posts/` named `YYYY-MM-DD-slug.md`. The file name sets the URL
(`/blog/YYYY/MM/DD/slug/`), and the front matter sets the title and date:

```md
---
title: "Learning to Walk"
date: 2017-10-04T02:48:02+05:30
---
```

Fenced code blocks with a language (` ```python `) are syntax highlighted.

## Where things are

- `src/site.ts`: site title, tagline, author
- `src/styles/global.css`: the whole design; colours and fonts are the custom properties at the top
- `src/scripts/landscape.ts`: the contour map and its gradient descent paths
- `src/layouts/Base.astro`: page shell (header, nav, footer)
- `src/pages/`: home, archive, post template, Atom feed, sitemap
- `public/fonts/`: HarshaFont, the handwriting face
