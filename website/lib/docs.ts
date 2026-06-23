import fs from 'fs'
import path from 'path'
import matter from 'gray-matter'
import type { Locale } from '@/lib/i18n'

const CONTENT_DIR = path.join(process.cwd(), 'content/docs')

export interface DocMeta {
  title: string
  description?: string
  section?: string
  order?: number
  slug: string[]
}

export interface Doc extends DocMeta {
  content: string
}

export function getAllDocs(): DocMeta[] {
  const docs: DocMeta[] = []

  function walk(dir: string, prefix: string[] = []) {
    const entries = fs.readdirSync(dir, { withFileTypes: true })
    for (const entry of entries) {
      if (entry.isDirectory()) {
        walk(path.join(dir, entry.name), [...prefix, entry.name])
      } else if (entry.name.endsWith('.mdx') || entry.name.endsWith('.md')) {
        const filePath = path.join(dir, entry.name)
        const raw = fs.readFileSync(filePath, 'utf-8')
        const { data } = matter(raw)
        const slug = [...prefix, entry.name.replace(/\.mdx?$/, '')]
        docs.push({
          title: data.title ?? slug[slug.length - 1],
          description: data.description,
          section: data.section,
          order: data.order ?? 99,
          slug,
        })
      }
    }
  }

  walk(CONTENT_DIR)
  return docs.sort((a, b) => (a.order ?? 99) - (b.order ?? 99))
}

export function getDocBySlug(slug: string[], locale: Locale = 'pt'): Doc | null {
  const dirs =
    locale === 'en'
      ? [path.join(CONTENT_DIR, 'en'), CONTENT_DIR]
      : [CONTENT_DIR]

  for (const dir of dirs) {
    const candidates = [
      path.join(dir, ...slug) + '.mdx',
      path.join(dir, ...slug) + '.md',
      path.join(dir, ...slug, 'index.mdx'),
      path.join(dir, ...slug, 'index.md'),
    ]
    for (const filePath of candidates) {
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8')
        const { data, content } = matter(raw)
        return {
          title: data.title ?? slug[slug.length - 1],
          description: data.description,
          section: data.section,
          order: data.order,
          slug,
          content,
        }
      }
    }
  }

  return null
}

export { NAV } from './nav'
