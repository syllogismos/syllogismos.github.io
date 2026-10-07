import { getCollection, type CollectionEntry } from 'astro:content';
import { SITE } from '../site';

export interface Post {
  entry: CollectionEntry<'posts'>;
  title: string;
  date: Date;
  year: string;
  /** Path below /blog/, e.g. 2017/10/04/learning-to-walk */
  slug: string;
  url: string;
  excerpt: string;
}

const ENTITIES: Record<string, string> = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };

function decode(text: string) {
  return text.replace(/&(#x?[0-9a-f]+|\w+);/gi, (match, code: string) => {
    if (code[0] !== '#') return ENTITIES[code] ?? match;
    const point = code[1].toLowerCase() === 'x' ? parseInt(code.slice(2), 16) : parseInt(code.slice(1), 10);
    return String.fromCodePoint(point);
  });
}

/** The first ~150 characters of a post's prose, skipping code blocks. */
function excerpt(html: string, length = 150) {
  const text = decode(html.replace(/<pre[\s\S]*?<\/pre>/g, ' ').replace(/<[^>]+>/g, ''))
    .replace(/\s+/g, ' ')
    .trim();
  if (text.length <= length) return text;
  return text.slice(0, text.lastIndexOf(' ', length)) + ' …';
}

/** All posts, newest first. The URL comes from the file name: YYYY-MM-DD-slug.md */
export async function getPosts(): Promise<Post[]> {
  const entries = await getCollection('posts');
  return entries
    .map((entry) => {
      const match = entry.id.match(/^(\d{4})-(\d{2})-(\d{2})-(.+)$/);
      if (!match) throw new Error(`Post file names must look like YYYY-MM-DD-slug.md, got "${entry.id}"`);
      const [, year, month, day, name] = match;
      const slug = `${year}/${month}/${day}/${name}`;
      return {
        entry,
        title: entry.data.title,
        date: entry.data.date,
        year,
        slug,
        url: `/blog/${slug}/`,
        excerpt: excerpt(entry.rendered?.html ?? ''),
      };
    })
    .sort((a, b) => b.date.valueOf() - a.date.valueOf());
}

const format = (options: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat('en-US', { timeZone: SITE.timeZone, ...options });

export const longDate = (date: Date) => format({ month: 'short', day: 'numeric', year: 'numeric' }).format(date);
export const shortDate = (date: Date) => format({ month: 'short', day: '2-digit' }).format(date);
