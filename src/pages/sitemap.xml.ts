import type { APIRoute } from 'astro';
import { getPosts } from '../lib/posts';

export const GET: APIRoute = async ({ site }) => {
  const posts = await getPosts();
  const url = (path: string, lastmod?: Date) =>
    `  <url>\n    <loc>${new URL(path, site)}</loc>${lastmod ? `\n    <lastmod>${lastmod.toISOString()}</lastmod>` : ''}\n  </url>`;
  const urls = [
    ...posts.map((post) => url(post.url, post.date)),
    url('/', posts[0]?.date),
    url('/blog/archives/', posts[0]?.date),
  ];
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join('\n')}
</urlset>
`;
  return new Response(sitemap, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
};
