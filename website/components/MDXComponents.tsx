import { cn } from '@/lib/utils'

export const mdxComponents = {
  h1: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1
      className={cn(
        'text-3xl font-bold text-white mt-8 mb-4 pb-3 border-b border-zinc-800',
        className
      )}
      {...props}
    />
  ),
  h2: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2
      className={cn('text-xl font-semibold text-white mt-10 mb-3 scroll-mt-20', className)}
      {...props}
    />
  ),
  h3: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3
      className={cn('text-base font-semibold text-zinc-100 mt-6 mb-2 scroll-mt-20', className)}
      {...props}
    />
  ),
  p: ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className={cn('text-zinc-300 leading-7 mb-4', className)} {...props} />
  ),
  a: ({ className, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a
      className={cn(
        'text-arc-300 hover:text-arc-200 underline underline-offset-4 decoration-arc-500/50 hover:decoration-arc-300 transition-colors',
        className
      )}
      {...props}
    />
  ),
  code: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => {
    const isBlock = className?.includes('language-')
    if (isBlock) return <code className={className} {...props} />
    return (
      <code
        className={cn(
          'font-mono text-[0.875em] text-arc-300 bg-zinc-800/80 rounded px-1.5 py-0.5 border border-zinc-700/50',
          className
        )}
        {...props}
      />
    )
  },
  pre: ({ className, ...props }: React.HTMLAttributes<HTMLPreElement>) => (
    <pre
      className={cn(
        'my-5 rounded-xl bg-zinc-900 border border-zinc-700/80 overflow-x-auto text-sm',
        'shadow-lg shadow-black/30',
        className
      )}
      {...props}
    />
  ),
  blockquote: ({ className, ...props }: React.HTMLAttributes<HTMLQuoteElement>) => (
    <blockquote
      className={cn(
        'border-l-4 border-arc-500 pl-4 py-1 my-4 text-zinc-400 italic bg-arc-500/5 rounded-r-lg',
        className
      )}
      {...props}
    />
  ),
  table: ({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) => (
    <div className="my-6 overflow-x-auto rounded-xl border border-zinc-800">
      <table className={cn('w-full text-sm', className)} {...props} />
    </div>
  ),
  thead: ({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => (
    <thead className={cn('bg-zinc-900 border-b border-zinc-700', className)} {...props} />
  ),
  th: ({ className, ...props }: React.HTMLAttributes<HTMLTableCellElement>) => (
    <th
      className={cn('px-4 py-3 text-left text-xs font-semibold text-zinc-300 uppercase tracking-wider', className)}
      {...props}
    />
  ),
  td: ({ className, ...props }: React.HTMLAttributes<HTMLTableCellElement>) => (
    <td
      className={cn('px-4 py-3 text-zinc-300 border-t border-zinc-800/60', className)}
      {...props}
    />
  ),
  ul: ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul className={cn('my-4 ml-4 space-y-1.5 list-none', className)} {...props} />
  ),
  ol: ({ className, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol className={cn('my-4 ml-4 space-y-1.5 list-decimal list-inside', className)} {...props} />
  ),
  li: ({ className, ...props }: React.HTMLAttributes<HTMLLIElement>) => (
    <li
      className={cn(
        'text-zinc-300 flex gap-2 items-start before:content-["▸"] before:text-arc-400 before:mt-0.5 before:shrink-0',
        className
      )}
      {...props}
    />
  ),
  hr: ({ className, ...props }: React.HTMLAttributes<HTMLHRElement>) => (
    <hr className={cn('my-8 border-zinc-800', className)} {...props} />
  ),
}

export function Callout({
  type = 'info',
  title,
  children,
}: {
  type?: 'info' | 'warning' | 'tip' | 'danger'
  title?: string
  children: React.ReactNode
}) {
  const styles = {
    info: 'border-blue-500/40 bg-blue-500/10 text-blue-300',
    warning: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-300',
    tip: 'border-arc-500/40 bg-arc-500/10 text-arc-300',
    danger: 'border-red-500/40 bg-red-500/10 text-red-300',
  }

  const icons = { info: 'ℹ', warning: '⚠', tip: '✦', danger: '✕' }

  return (
    <div className={`my-5 border rounded-xl p-4 ${styles[type]}`}>
      {title && (
        <p className="font-semibold mb-1 flex items-center gap-2">
          <span>{icons[type]}</span>
          {title}
        </p>
      )}
      <div className="text-sm leading-relaxed opacity-90">{children}</div>
    </div>
  )
}
