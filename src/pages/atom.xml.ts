import type { APIRoute } from 'astro';
import { getPosts } from '../lib/posts';
import { SITE } from '../site';

// Entry ids keep the form the old Octopress feed used, so feed readers don't re-announce old posts.
const LEGACY_ORIGIN = 'http://syllogismos.github.io';

const cdata = (text: string) => `<![CDATA[${text.replaceAll(']]>', ']]]]><![CDATA[>')}]]>`;

export const GET: APIRoute = async ({ site }) => {
  const posts = await getPosts();
  const entries = posts.map(
    (post) => `  <entry>
    <title type="html">${cdata(post.title)}</title>
    <link href="${new URL(post.url, site)}"/>
    <updated>${post.date.toISOString()}</updated>
    <id>${LEGACY_ORIGIN}/blog/${post.slug}</id>
    <content type="html">${cdata(post.entry.rendered?.html ?? '')}</content>
  </entry>`,
  );
  const feed = `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>${cdata(SITE.title)}</title>
  <link href="${new URL('/atom.xml', site)}" rel="self"/>
  <link href="${site}"/>
  <updated>${(posts[0]?.date ?? new Date()).toISOString()}</updated>
  <id>${LEGACY_ORIGIN}/</id>
  <author>
    <name>${cdata(SITE.author)}</name>
  </author>
${entries.join('\n')}
</feed>
`;
  return new Response(feed, { headers: { 'Content-Type': 'application/atom+xml; charset=utf-8' } });
};
