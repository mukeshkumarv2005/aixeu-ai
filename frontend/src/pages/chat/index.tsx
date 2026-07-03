/** Chat page — AI conversation interface with streaming responses.

Layout: sidebar (conversation list) + main area (messages + input).
Covers all states: loading, error, empty, streaming, and edge cases.
*/

import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  Loader2,
  AlertCircle,
  PanelLeftOpen,
  PanelLeftClose,
  Bot,
  Sparkles,
  ListTodo,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { useChatStore, useIsStreaming, useActiveMessages } from '@/stores/chat'
import { useKnowledgeBases } from '@/api/knowledge'
import { MarkdownRenderer } from '@/components/chat/markdown'
import type { ConversationResponse } from '@/stores/chat'
import { RelatedTasksWidget } from '@/components/tasks/RelatedTasksWidget'
import { useAIConvertChat } from '@/api/task-ai'

export default function ChatPage() {
  // ── Store state ───────────────────────────────────────────────────────────
  const {
    conversations,
    conversationsLoading,
    conversationsError,
    currentConversationId,
    messagesLoading,
    messagesError,
    streamError,
    streamingContent,
    listConversations,
    createConversation,
    deleteConversation,
    setCurrentConversation,
    sendMessage,
  } = useChatStore()
  const isStreaming = useIsStreaming()
  const messages = useActiveMessages()
  const user = useAuthStore((s) => s.user)

  // ── Local state ───────────────────────────────────────────────────────────
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [isAtBottom, setIsAtBottom] = useState(true)
  const [sending, setSending] = useState(false)
  const [selectedKbId, setSelectedKbId] = useState<string>('')

  // ── Knowledge bases for RAG ──────────────────────────────────────────────
  const { data: kbData } = useKnowledgeBases(0, 50)
  const knowledgeBases = kbData?.items ?? []
  const convertMutation = useAIConvertChat()
  const [convertError, setConvertError] = useState<string | null>(null)

  // ── Refs ──────────────────────────────────────────────────────────────────
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // ── Load conversations on mount ───────────────────────────────────────────
  useEffect(() => {
    listConversations()
  }, [listConversations])

  // ── Auto-scroll ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (isAtBottom) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, streamingContent, isAtBottom])

  // ── Auto-resize textarea ─────────────────────────────────────────────────
  const adjustTextarea = useCallback(() => {
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = 'auto'
      ta.style.height = Math.min(ta.scrollHeight, 200) + 'px'
    }
  }, [])

  useEffect(() => {
    adjustTextarea()
  }, [input, adjustTextarea])

  // ── Scroll handler ────────────────────────────────────────────────────────
  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const el = e.currentTarget
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
      setIsAtBottom(atBottom)
    },
    [],
  )

  // ── New conversation ──────────────────────────────────────────────────────
  const handleNewChat = useCallback(async () => {
    try {
      const conv = await createConversation()
      setCurrentConversation(conv.id)
    } catch {
      // error is handled by the store
    }
  }, [createConversation, setCurrentConversation])

  // ── Delete conversation ──────────────────────────────────────────────────
  const handleDelete = useCallback(
    async (e: React.MouseEvent, id: string) => {
      e.stopPropagation()
      const conv = conversations.find((c) => c.id === id)
      const title = conv?.title || 'untitled'
      if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return
      await deleteConversation(id)
    },
    [conversations, deleteConversation],
  )

  // ── Send message ──────────────────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || !currentConversationId || sending) return

    setInput('')
    setSending(true)
    try {
      await sendMessage(text, undefined, selectedKbId || undefined)
    } finally {
      setSending(false)

      // Re-focus the input after streaming finishes
      textareaRef.current?.focus()
    }
  }, [input, currentConversationId, sending, sendMessage, selectedKbId])

  // ── Keyboard shortcut ────────────────────────────────────────────────────
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  // ── Convert chat to task ─────────────────────────────────────────────────
  const handleConvertToTask = useCallback(async () => {
    if (!currentConversationId) return
    setConvertError(null)
    try {
      const res = await convertMutation.mutateAsync({
        conversation_id: currentConversationId,
      })
      navigate('/tasks/create', { state: { draftFromConvert: res.task } })
    } catch (err: any) {
      setConvertError(err?.message ?? 'Failed to convert to task.')
    }
  }, [currentConversationId, convertMutation, navigate])

  // ── Sidebar items helper ─────────────────────────────────────────────────
  const formatDate = (iso: string | null) => {
    if (!iso) return ''
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffDays = Math.floor(diffMs / 86_400_000)

    if (diffDays === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays}d ago`
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
  }

  // ── Render: welcome screen ──────────────────────────────────────────────
  const renderWelcome = () => (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4">
      <div className="rounded-2xl bg-primary-100 p-4 dark:bg-primary-900/30">
        <Sparkles size={40} className="text-primary-500" />
      </div>
      <h2 className="text-xl font-semibold text-surface-800 dark:text-surface-200">
        Welcome{user?.display_name ? `, ${user.display_name}` : ''}
      </h2>
      <p className="max-w-sm text-center text-sm text-surface-500">
        Start a new conversation or select one from the sidebar.
      </p>
      <button
        onClick={handleNewChat}
        className="mt-2 flex items-center gap-2 rounded-xl bg-primary-500 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-600"
      >
        <Plus size={18} />
        New Chat
      </button>
    </div>
  )

  // ── Render: empty conversation ──────────────────────────────────────────
  const renderEmptyConversation = () => (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4">
      <Bot size={36} className="text-surface-400" />
      <p className="text-sm text-surface-500">
        Send a message to start the conversation.
      </p>
    </div>
  )

  // ── Render: message bubbles ─────────────────────────────────────────────
  const renderMessages = () => (
    <div className="flex-1 space-y-4 px-4 py-6">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={cn(
            'flex',
            msg.role === 'user' ? 'justify-end' : 'justify-start',
          )}
        >
          <div
            className={cn(
              'max-w-[85%] rounded-2xl px-4 py-2.5 lg:max-w-[70%]',
              msg.role === 'user'
                ? 'bg-primary-500 text-white'
                : 'bg-surface-100 text-surface-800 dark:bg-surface-800 dark:text-surface-200',
            )}
          >
            {msg.role === 'assistant' ? (
              <MarkdownRenderer content={msg.content} />
            ) : (
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                {msg.content}
              </p>
            )}
          </div>
        </div>
      ))}

      {/* Streaming message */}
      {isStreaming && streamingContent && (
        <div className="flex justify-start">
          <div className="max-w-[85%] rounded-2xl bg-surface-100 px-4 py-2.5 text-surface-800 dark:bg-surface-800 dark:text-surface-200 lg:max-w-[70%]">
            <MarkdownRenderer content={streamingContent} />
            <span className="inline-block h-4 w-2 animate-pulse rounded-full bg-primary-500 align-text-bottom" />
          </div>
        </div>
      )}

      {/* Streaming started but no content yet */}
      {isStreaming && !streamingContent && (
        <div className="flex justify-start">
          <div className="flex items-center gap-2 rounded-2xl bg-surface-100 px-4 py-3 text-surface-500 dark:bg-surface-800">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">Thinking…</span>
          </div>
        </div>
      )}

      {/* Stream error */}
      {streamError && !isStreaming && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>{streamError}</span>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  )

  // ── Render: input bar ───────────────────────────────────────────────────
  const renderInput = () => (
    <div className="border-t border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950">
      <div className="mx-auto flex max-w-4xl items-end gap-2">
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isStreaming ? 'Waiting for response…' : 'Type a message…'
            }
            disabled={isStreaming || !currentConversationId}
            rows={1}
            className={cn(
              'w-full resize-none rounded-xl border bg-surface-50 px-4 py-2.5 pr-12 text-sm leading-relaxed outline-none transition-colors',
              'placeholder:text-surface-400',
              'border-surface-300 focus:border-primary-400 focus:ring-2 focus:ring-primary-100',
              'dark:border-surface-700 dark:bg-surface-900 dark:focus:border-primary-500 dark:focus:ring-primary-900/30',
              'disabled:cursor-not-allowed disabled:opacity-50',
            )}
          />
        </div>
        <button
          onClick={handleSend}
          disabled={
            !input.trim() || isStreaming || sending || !currentConversationId
          }
          className={cn(
            'flex shrink-0 items-center justify-center rounded-xl p-2.5 transition-colors',
            input.trim() && !isStreaming && !sending
              ? 'bg-primary-500 text-white hover:bg-primary-600'
              : 'bg-surface-200 text-surface-400 dark:bg-surface-800',
            'disabled:cursor-not-allowed',
          )}
          title="Send message (Enter)"
        >
          {sending ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Send size={18} />
          )}
        </button>
      </div>
    </div>
  )

  // ── Render: sidebar ─────────────────────────────────────────────────────
  const renderSidebar = () => (
    <aside
      className={cn(
        'flex flex-col border-r border-surface-200 bg-white transition-all duration-200 dark:border-surface-800 dark:bg-surface-950',
        sidebarOpen ? 'w-72' : 'w-0 overflow-hidden',
      )}
    >
      {/* Sidebar header */}
      <div className="flex items-center gap-2 border-b border-surface-200 p-3 dark:border-surface-800">
        <button
          onClick={handleNewChat}
          className="flex flex-1 items-center gap-2 rounded-xl bg-primary-500 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-600"
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto p-2">
        {conversationsLoading && conversations.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={20} className="animate-spin text-surface-400" />
          </div>
        ) : conversationsError && conversations.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-3 py-8 text-center">
            <AlertCircle size={20} className="text-red-400" />
            <p className="text-xs text-red-500">{conversationsError}</p>
            <button
              onClick={listConversations}
              className="mt-1 text-xs font-medium text-primary-500 hover:text-primary-600"
            >
              Retry
            </button>
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-3 py-8 text-center">
            <MessageSquare size={24} className="text-surface-400" />
            <p className="text-xs text-surface-500">No conversations yet</p>
          </div>
        ) : (
          <ul className="space-y-1">
            {conversations.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isActive={conv.id === currentConversationId}
                onClick={() => setCurrentConversation(conv.id)}
                onDelete={(e) => handleDelete(e, conv.id)}
                formatDate={formatDate}
              />
            ))}
          </ul>
        )}
      </div>

      {/* Related Tasks — shown only when a conversation is active */}
      {currentConversationId && (
        <div className="border-t border-surface-200 p-3 dark:border-surface-800">
          <RelatedTasksWidget chatConversationId={currentConversationId} maxTasks={3} />
        </div>
      )}
    </aside>
  )

  // ── Main render ──────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen bg-surface-50 dark:bg-surface-950">
      {/* Sidebar */}
      <div className="flex">
        {renderSidebar()}

        {/* Toggle button */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="flex items-center justify-center border-r border-surface-200 bg-white px-1.5 text-surface-400 hover:text-surface-600 dark:border-surface-800 dark:bg-surface-950 dark:hover:text-surface-300"
          title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
        >
          {sidebarOpen ? (
            <PanelLeftClose size={16} />
          ) : (
            <PanelLeftOpen size={16} />
          )}
        </button>
      </div>

      {/* Main area */}
      <div className="flex flex-1 flex-col">
        {/* Messages header */}
        {currentConversationId && (
          <>
          <div className="flex items-center justify-between border-b border-surface-200 bg-white px-4 py-2 dark:border-surface-800 dark:bg-surface-950">
            <div className="flex items-center">
              <Bot size={18} className="mr-2 text-primary-500" />
              {(() => {
                const conv = conversations.find(
                  (c) => c.id === currentConversationId,
                )
                return (
                  <span className="truncate text-sm font-medium text-surface-700 dark:text-surface-300">
                    {conv?.title || 'New Chat'}
                  </span>
                )
              })()}
            </div>

            {/* KB selector */}
            {knowledgeBases.length > 0 && (
              <select
                value={selectedKbId}
                onChange={(e) => setSelectedKbId(e.target.value)}
                className="max-w-[200px] rounded-lg border border-surface-300 bg-white px-2 py-1 text-xs text-surface-700 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300"
                title="Attach knowledge base for RAG"
              >
                <option value="">No KB attached</option>
                {knowledgeBases.map((kb) => (
                  <option key={kb.id} value={kb.id}>
                    {kb.name}
                  </option>
                ))}
              </select>
            )}

            {/* Convert to Task */}
            <button
              onClick={handleConvertToTask}
              disabled={convertMutation.isPending}
              className="flex items-center gap-2 rounded-lg border border-primary-200 bg-primary-50 px-3 py-1.5 text-xs font-medium text-primary-700 hover:bg-primary-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-primary-900/30 dark:bg-primary-900/20 dark:text-primary-400 dark:hover:bg-primary-900/30 transition-colors"
            >
              {convertMutation.isPending ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <ListTodo size={12} />
              )}
              {convertMutation.isPending ? 'Converting…' : 'Task'}
            </button>
          </div>

          {/* Convert error */}
          {convertError && (
            <div className="flex items-center gap-2 border-b border-surface-200 bg-red-50 px-4 py-2 text-xs text-red-600 dark:border-surface-800 dark:bg-red-900/10 dark:text-red-400">
              <AlertCircle size={12} />
              {convertError}
            </div>
          )}
        </>)}

        {/* Messages area */}
        <div
          ref={messagesContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto"
        >
          {/* Loading state for messages */}
          {messagesLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-surface-400" />
            </div>
          ) : messagesError ? (
            <div className="mx-auto max-w-md px-4 py-16 text-center">
              <AlertCircle size={32} className="mx-auto text-red-400" />
              <p className="mt-3 text-sm text-red-500">{messagesError}</p>
            </div>
          ) : !currentConversationId ? (
            renderWelcome()
          ) : messages.length === 0 && !isStreaming ? (
            renderEmptyConversation()
          ) : (
            renderMessages()
          )}
        </div>

        {/* Input */}
        {currentConversationId ? renderInput() : null}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ConversationItem (extracted for clarity)
// ---------------------------------------------------------------------------

function ConversationItem({
  conversation: conv,
  isActive,
  onClick,
  onDelete,
  formatDate,
}: {
  conversation: ConversationResponse
  isActive: boolean
  onClick: () => void
  onDelete: (e: React.MouseEvent) => void
  formatDate: (iso: string | null) => string
}) {
  const [showDelete, setShowDelete] = useState(false)
  const isStreaming = useIsStreaming()

  return (
    <li>
      <button
        onClick={onClick}
        disabled={isStreaming}
        onMouseEnter={() => setShowDelete(true)}
        onMouseLeave={() => setShowDelete(false)}
        className={cn(
          'group flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors',
          isActive
            ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300'
            : 'text-surface-700 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800',
          isStreaming && 'cursor-not-allowed opacity-50',
        )}
      >
        <MessageSquare
          size={14}
          className={cn(
            'shrink-0',
            isActive
              ? 'text-primary-500'
              : 'text-surface-400 group-hover:text-surface-500',
          )}
        />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">
            {conv.title || 'New Chat'}
          </p>
          <p className="truncate text-xs text-surface-400">
            {formatDate(conv.updated_at || conv.created_at)}
          </p>
        </div>

        {/* Delete button (visible on hover) */}
        <button
          onClick={onDelete}
          className={cn(
            'shrink-0 rounded-lg p-1.5 text-surface-400 transition-all hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20 dark:hover:text-red-400',
            showDelete
              ? 'translate-x-0 opacity-100'
              : 'translate-x-1 opacity-0',
          )}
          title="Delete conversation"
        >
          <Trash2 size={14} />
        </button>
      </button>
    </li>
  )
}
