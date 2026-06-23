import { notFound } from 'next/navigation'
import { cookies } from 'next/headers'
import { MDXRemote } from 'next-mdx-remote/rsc'
import { getDocBySlug } from '@/lib/docs'
import { getNav } from '@/lib/nav'
import { mdxComponents, Callout } from '@/components/MDXComponents'
import { slugToHref } from '@/lib/utils'
import Link from 'next/link'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { Metadata } from 'next'
import type { Locale } from '@/lib/i18n'
import { i18n, tr } from '@/lib/i18n'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'

interface Props {
  params: Promise<{ slug: string[] }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const doc = getDocBySlug(slug)
  if (!doc) return {}
  return {
    title: doc.title,
    description: doc.description,
  }
}

function getAdjacentDocs(slug: string[], locale: Locale) {
  const allItems = getNav(locale).flatMap((g) => g.items)
  const currentHref = slugToHref(slug)
  const idx = allItems.findIndex((item) => slugToHref(item.slug) === currentHref)
  return {
    prev: idx > 0 ? allItems[idx - 1] : null,
    next: idx < allItems.length - 1 ? allItems[idx + 1] : null,
  }
}

export default async function DocPage({ params }: Props) {
  const { slug } = await params

  const store = await cookies()
  const lang = (store.get('arc-lang')?.value ?? 'pt') as Locale

  const doc = getDocBySlug(slug, lang)
  if (!doc) notFound()

  const { prev, next } = getAdjacentDocs(slug, lang)

  return (
    <article>
      {doc.section && (
        <p className="text-xs font-semibold uppercase tracking-wider text-arc-400 mb-2">
          {doc.section}
        </p>
      )}
      <h1 className="text-3xl font-bold text-white mb-2">{doc.title}</h1>
      {doc.description && (
        <p className="text-lg text-zinc-400 mb-8 leading-relaxed border-b border-zinc-800 pb-8">
          {doc.description}
        </p>
      )}

      <div className="prose prose-invert max-w-none">
        <MDXRemote
          source={doc.content}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          components={{ ...mdxComponents, Callout } as any}
          options={{
            mdxOptions: {
              remarkPlugins: [remarkGfm],
              rehypePlugins: [rehypeHighlight],
            },
          }}
        />
      </div>

      {(prev || next) && (
        <nav className="mt-16 pt-8 border-t border-zinc-800 flex flex-col sm:flex-row gap-4">
          {prev && (
            <Link
              href={slugToHref(prev.slug)}
              className="flex items-center gap-3 p-4 rounded-xl border border-zinc-800 hover:border-zinc-600 bg-zinc-900/50 hover:bg-zinc-900 transition-all group flex-1"
            >
              <ChevronLeft
                size={16}
                className="text-zinc-500 group-hover:text-arc-400 transition-colors shrink-0"
              />
              <div className="min-w-0">
                <p className="text-xs text-zinc-500 mb-0.5">{tr(i18n.doc.prev, lang)}</p>
                <p className="text-sm font-medium text-white truncate">{prev.title}</p>
              </div>
            </Link>
          )}
          {next && (
            <Link
              href={slugToHref(next.slug)}
              className="flex items-center gap-3 p-4 rounded-xl border border-zinc-800 hover:border-zinc-600 bg-zinc-900/50 hover:bg-zinc-900 transition-all group flex-1 sm:text-right sm:flex-row-reverse"
            >
              <ChevronRight
                size={16}
                className="text-zinc-500 group-hover:text-arc-400 transition-colors shrink-0"
              />
              <div className="min-w-0">
                <p className="text-xs text-zinc-500 mb-0.5">{tr(i18n.doc.next, lang)}</p>
                <p className="text-sm font-medium text-white truncate">{next.title}</p>
              </div>
            </Link>
          )}
        </nav>
      )}
    </article>
  )
}
