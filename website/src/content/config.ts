import { defineCollection, z } from 'astro:content';

const posts = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    date: z.coerce.date(),
    category: z.enum(['essay', 'note', 'openo1-log', 'research-note', 'principle']),
    draft: z.boolean().default(false)
  })
});

export const collections = { posts };
