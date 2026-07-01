/** Chat store using Zustand — manages conversations, messages, and SSE streaming.

Conversations are listed, created, updated, and deleted via the API.
Messages are fetched for the active conversation, and streaming AI responses
are read incrementally from a Server-Sent Events (SSE) stream.
*/

import { create } from 'zustand'
import { apiClient } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ConversationResponse {
  id: string
  title: string | null
  model: string
  is_archived: boolean
  created_at: string
  updated_at: string | null
  message_count: number
}

export interface ConversationList {
  conversations: ConversationResponse[]
  total: number
}

export interface MessageResponse {
  id: string
  conversation_id: string
  role: string
  content: string
  input_tokens: number | null
  output_tokens: number | null
  model: string | null
  created_at: string
}

export interface MessageList {
  messages: MessageResponse[]
  total: number
}

interface StreamChunk {
  type: string
  content?: string
  finish_reason?: string | null
  message_id?: string | null
  input_tokens?: number | null
  output_tokens?: number | null
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

export interface ChatState {
  conversations: ConversationResponse[]
  conversationsLoading: boolean
  conversationsError: string | null
  currentConversationId: string | null
  messages: MessageResponse[]
  messagesLoading: boolean
  messagesError: string | null
  isStreaming: boolean
  streamingContent: string
  streamError: string | null
}

export interface ChatActions {
  /** Fetch all non-archived conversations for the current user. */
  listConversations: () => Promise<void>

  /** Create a new conversation and return it. */
  createConversation: (body?: {
    title?: string
    model?: string
  }) => Promise<ConversationResponse>

  /** Update conversation title and/or archive status. */
  updateConversation: (
    id: string,
    body: { title?: string; is_archived?: boolean },
  ) => Promise<ConversationResponse>

  /** Delete a conversation and its messages. */
  deleteConversation: (id: string) => Promise<void>

  /** Switch the active conversation and load its messages. */
  setCurrentConversation: (id: string | null) => void

  /** Fetch messages for a conversation. */
  loadMessages: (conversationId: string) => Promise<void>

  /** Send a message and stream the AI response via SSE. */
  sendMessage: (content: string, model?: string) => Promise<void>

  /** Clear the streaming state. */
  clearStream: () => void
}

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

const initialState: ChatState = {
  conversations: [],
  conversationsLoading: false,
  conversationsError: null,
  currentConversationId: null,
  messages: [],
  messagesLoading: false,
  messagesError: null,
  isStreaming: false,
  streamingContent: '',
  streamError: null,
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useChatStore = create<ChatState & ChatActions>((set, get) => ({
  ...initialState,

  listConversations: async () => {
    set({ conversationsLoading: true, conversationsError: null })
    try {
      const result = await apiClient.get<ConversationList>(
        '/chat/conversations',
      )
      set({
        conversations: result.conversations,
        conversationsLoading: false,
      })
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to list conversations'
      set({ conversationsLoading: false, conversationsError: message })
    }
  },

  createConversation: async (body) => {
    const result = await apiClient.post<ConversationResponse>(
      '/chat/conversations',
      {
        title: body?.title ?? null,
        model: body?.model ?? 'gpt-4o',
      },
    )
    set((state) => ({
      conversations: [result, ...state.conversations],
    }))
    return result
  },

  updateConversation: async (id, body) => {
    const result = await apiClient.put<ConversationResponse>(
      `/chat/conversations/${id}`,
      body,
    )
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? result : c,
      ),
    }))
    return result
  },

  deleteConversation: async (id) => {
    await apiClient.delete(`/chat/conversations/${id}`)
    const { currentConversationId } = get()
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      ...(currentConversationId === id
        ? { currentConversationId: null, messages: [] }
        : {}),
    }))
  },

  setCurrentConversation: (id) => {
    set({
      currentConversationId: id,
      messages: [],
      streamingContent: '',
      isStreaming: false,
      streamError: null,
    })
    if (id) {
      get().loadMessages(id)
    }
  },

  loadMessages: async (conversationId) => {
    set({ messagesLoading: true, messagesError: null })
    try {
      const result = await apiClient.get<MessageList>(
        `/chat/conversations/${conversationId}/messages`,
      )
      set({ messages: result.messages, messagesLoading: false })
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to load messages'
      set({ messagesLoading: false, messagesError: message })
    }
  },

  sendMessage: async (content, model) => {
    const { currentConversationId } = get()
    if (!currentConversationId) return

    // Add user message immediately for optimistic UI
    const userMessage: MessageResponse = {
      id: crypto.randomUUID(),
      conversation_id: currentConversationId,
      role: 'user',
      content,
      input_tokens: null,
      output_tokens: null,
      model: null,
      created_at: new Date().toISOString(),
    }

    set((state) => ({
      messages: [...state.messages, userMessage],
      isStreaming: true,
      streamingContent: '',
      streamError: null,
    }))

    try {
      const token = useAuthStore.getState().accessToken
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const response = await fetch(
        `/api/v1/chat/conversations/${currentConversationId}/messages`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ content, model }),
          credentials: 'include',
        },
      )

      if (!response.ok) {
        let detail = response.statusText
        try {
          const errBody = await response.json()
          detail = errBody.detail ?? detail
        } catch {
          // ignore parse failure
        }
        set({ isStreaming: false, streamError: detail })
        return
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullResponse = ''
      let savedMessageId: string | null = null
      let inputTokens: number | null = null
      let outputTokens: number | null = null

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        // Keep the (possibly partial) last line in the buffer
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()

          // Skip empty lines and SSE comments
          if (!trimmed || trimmed.startsWith(':')) continue

          // Check for event data
          if (trimmed.startsWith('data: ')) {
            const data = trimmed.slice(6)

            // Terminal sentinel
            if (data === '[DONE]') continue

            try {
              const chunk: StreamChunk = JSON.parse(data)

              if (chunk.type === 'chunk' && chunk.content) {
                fullResponse += chunk.content
                set({ streamingContent: fullResponse })
              } else if (chunk.type === 'done') {
                savedMessageId = chunk.message_id ?? null
                inputTokens = chunk.input_tokens ?? null
                outputTokens = chunk.output_tokens ?? null
              } else if (chunk.type === 'error') {
                set({ streamError: chunk.content ?? 'AI error', isStreaming: false })
              }
            } catch {
              // Ignore malformed JSON chunks
            }
          }
        }
      }

      // Streaming complete — add assistant message to conversation
      const assistantMessage: MessageResponse = {
        id: savedMessageId ?? crypto.randomUUID(),
        conversation_id: currentConversationId,
        role: 'assistant',
        content: fullResponse,
        input_tokens: inputTokens,
        output_tokens: outputTokens,
        model: model ?? null,
        created_at: new Date().toISOString(),
      }

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        isStreaming: false,
        streamingContent: '',
      }))

      // Refresh conversations list (title may have been auto-generated)
      get().listConversations()
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Stream failed'
      set({ isStreaming: false, streamError: message })
    }
  },

  clearStream: () => {
    set({ streamingContent: '', streamError: null, isStreaming: false })
  },
}))

/** Convenience selector: true while the AI is streaming a response. */
export const useIsStreaming = () => useChatStore((s) => s.isStreaming)

/** Convenience selector: the current streaming content. */
export const useStreamingContent = () =>
  useChatStore((s) => s.streamingContent)

/** Convenience selector: messages for the active conversation. */
export const useActiveMessages = () => useChatStore((s) => s.messages)
