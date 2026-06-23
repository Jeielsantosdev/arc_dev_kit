import Link from 'next/link'

export function Logo({ className }: { className?: string }) {
  return (
    <Link href="/" className={`flex items-center gap-2 group ${className ?? ''}`}>
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-arc-400 to-arc-600 flex items-center justify-center shadow-lg shadow-arc-500/30">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="text-white">
          <path
            d="M12 2L3 7v10l9 5 9-5V7L12 2z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <path
            d="M12 2v20M3 7l9 5 9-5"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="0.6"
          />
        </svg>
      </div>
      <div className="flex flex-col leading-none">
        <span className="text-white font-semibold text-sm tracking-wide">Arc DevKit</span>
        <span className="text-arc-400 text-[10px] font-medium tracking-wider uppercase">Docs</span>
      </div>
    </Link>
  )
}
