/** Renders AI markdown responses with syntax-highlighted code blocks, tables, and GFM support. */

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import {
  oneLight,
  oneDark,
} from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Check, Copy } from 'lucide-react'
import { useThemeStore } from '@/stores/theme'
import { cn } from '@/lib/utils'
import type { Components } from 'react-markdown'

// ---------------------------------------------------------------------------
// Code block wrapper with copy button
// ---------------------------------------------------------------------------

function CodeBlock({
  className,
  children,
}: {
  className?: string
  children?: React.ReactNode
}) {
  const [copied, setCopied] = useState(false)
  const match = /language-(\w+)/.exec(className ?? '')
  const code = String(children).replace(/\n$/, '')
  const resolvedTheme = useThemeStore.getState().resolvedTheme()
  const style = resolvedTheme === 'dark' ? oneDark : oneLight

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="group relative my-3 overflow-hidden rounded-lg border border-surface-200 dark:border-surface-800">
      {/* Language label + copy button */}
      <div className="flex items-center justify-between bg-surface-100 px-4 py-1.5 text-xs text-surface-500 dark:bg-surface-900 dark:text-surface-400">
        <span className="font-mono uppercase">
          {match?.[1] ?? 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded px-2 py-0.5 text-surface-400 transition-colors hover:bg-surface-200 hover:text-surface-700 dark:hover:bg-surface-800 dark:hover:text-surface-300"
          title="Copy code"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>

      <SyntaxHighlighter
        style={style}
        language={match?.[1] ?? 'text'}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: 0,
          fontSize: '0.8125rem',
          lineHeight: 1.6,
        }}
        showLineNumbers={false}
        wrapLongLines
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Markdown components map
// ---------------------------------------------------------------------------

const components: Components = {
  code({ className, children, ...props }) {
    const isInline = !className
    if (isInline) {
      return (
        <code
          className="rounded bg-surface-100 px-1.5 py-0.5 text-sm font-mono text-primary-700 dark:bg-surface-800 dark:text-primary-300"
          {...props}
        >
          {children}
        </code>
      )
    }
    return <CodeBlock className={className}>{children}</CodeBlock>
  },

  pre({ children }) {
    return <>{children}</>
  },

  a({ href, children, ...props }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary-600 underline decoration-primary-300 underline-offset-2 hover:text-primary-800 dark:text-primary-400 dark:decoration-primary-700 dark:hover:text-primary-200"
        {...props}
      >
        {children}
      </a>
    )
  },

  table({ children, ...props }) {
    return (
      <div className="my-3 overflow-x-auto rounded-lg border border-surface-200 dark:border-surface-800">
        <table
          className="min-w-full divide-y divide-surface-200 text-sm dark:divide-surface-800"
          {...props}
        >
          {children}
        </table>
      </div>
    )
  },

  th({ children, ...props }) {
    return (
      <th
        className="bg-surface-100 px-4 py-2 text-left text-xs font-semibold uppercase text-surface-600 dark:bg-surface-900 dark:text-surface-400"
        {...props}
      >
        {children}
      </th>
    )
  },

  td({ children, ...props }) {
    return (
      <td
        className="border-t border-surface-200 px-4 py-2 text-surface-700 dark:border-surface-800 dark:text-surface-300"
        {...props}
      >
        {children}
      </td>
    )
  },

  blockquote({ children, ...props }) {
    return (
      <blockquote
        className="my-3 border-l-4 border-primary-300 bg-surface-100/50 py-2 pl-4 italic text-surface-600 dark:border-primary-700 dark:bg-surface-900/50 dark:text-surface-400"
        {...props}
      >
        {children}
      </blockquote>
    )
  },

  hr(props) {
    return (
      <hr
        className="my-6 border-surface-200 dark:border-surface-800"
        {...props}
      />
    )
  },

  p({ children, ...props }) {
    return (
      <p className="my-2 leading-relaxed" {...props}>
        {children}
      </p>
    )
  },

  ul({ children, ...props }) {
    return (
      <ul className="my-2 list-disc space-y-1 pl-6" {...props}>
        {children}
      </ul>
    )
  },

  ol({ children, ...props }) {
    return (
      <ol className="my-2 list-decimal space-y-1 pl-6" {...props}>
        {children}
      </ol>
    )
  },

  li({ children, ...props }) {
    return (
      <li className="leading-relaxed" {...props}>
        {children}
      </li>
    )
  },

  h1({ children, ...props }) {
    return (
      <h1 className="my-4 text-xl font-bold" {...props}>
        {children}
      </h1>
    )
  },

  h2({ children, ...props }) {
    return (
      <h2 className="my-3 text-lg font-semibold" {...props}>
        {children}
      </h2>
    )
  },

  h3({ children, ...props }) {
    return (
      <h3 className="my-3 text-base font-semibold" {...props}>
        {children}
      </h3>
    )
  },

  strong({ children, ...props }) {
    return (
      <strong className="font-semibold" {...props}>
        {children}
      </strong>
    )
  },
}

// ---------------------------------------------------------------------------
// MarkdownRenderer
// ---------------------------------------------------------------------------

interface Props {
  content: string
  className?: string
}

export function MarkdownRenderer({ content, className }: Props) {
  return (
    <div className={cn('text-surface-800 dark:text-surface-200', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
