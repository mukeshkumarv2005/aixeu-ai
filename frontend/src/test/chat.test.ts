import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useChatStore } from '../stores/chat'
import { apiClient } from '../lib/api'
import { useAuthStore } from '../stores/auth'

vi.mock('../lib/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    upload: vi.fn(),
  },
}))

describe('Chat Store', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useChatStore.setState({
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
    })
    useAuthStore.setState({
      accessToken: 'test-token',
    })
  })

  it('lists conversations successfully', async () => {
    const mockList = {
      conversations: [{ id: 'conv-1', title: 'Conversation 1', model: 'gpt-4o', is_archived: false, created_at: '', updated_at: null, message_count: 0 }],
      total: 1,
    }
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockList)

    await useChatStore.getState().listConversations()

    expect(apiClient.get).toHaveBeenCalledWith('/chat/conversations')
    expect(useChatStore.getState().conversations).toEqual(mockList.conversations)
    expect(useChatStore.getState().conversationsLoading).toBe(false)
  })

  it('creates conversation successfully', async () => {
    const newConv = { id: 'conv-2', title: 'New Conv', model: 'gpt-4o', is_archived: false, created_at: '', updated_at: null, message_count: 0 }
    vi.mocked(apiClient.post).mockResolvedValueOnce(newConv)

    const result = await useChatStore.getState().createConversation({ title: 'New Conv' })

    expect(apiClient.post).toHaveBeenCalledWith('/chat/conversations', {
      title: 'New Conv',
      model: 'gpt-4o',
    })
    expect(result).toEqual(newConv)
    expect(useChatStore.getState().conversations[0]).toEqual(newConv)
  })

  it('updates conversation successfully', async () => {
    const existingConv = { id: 'conv-1', title: 'Conv 1', model: 'gpt-4o', is_archived: false, created_at: '', updated_at: null, message_count: 0 }
    const updatedConv = { ...existingConv, title: 'Updated Conv' }
    useChatStore.setState({ conversations: [existingConv] })
    vi.mocked(apiClient.put).mockResolvedValueOnce(updatedConv)

    await useChatStore.getState().updateConversation('conv-1', { title: 'Updated Conv' })

    expect(apiClient.put).toHaveBeenCalledWith('/chat/conversations/conv-1', {
      title: 'Updated Conv',
    })
    expect(useChatStore.getState().conversations[0].title).toBe('Updated Conv')
  })

  it('deletes conversation successfully', async () => {
    const existingConv = { id: 'conv-1', title: 'Conv 1', model: 'gpt-4o', is_archived: false, created_at: '', updated_at: null, message_count: 0 }
    useChatStore.setState({
      conversations: [existingConv],
      currentConversationId: 'conv-1',
    })
    vi.mocked(apiClient.delete).mockResolvedValueOnce({})

    await useChatStore.getState().deleteConversation('conv-1')

    expect(apiClient.delete).toHaveBeenCalledWith('/chat/conversations/conv-1')
    expect(useChatStore.getState().conversations).toHaveLength(0)
    expect(useChatStore.getState().currentConversationId).toBeNull()
  })

  it('sets active conversation and loads its messages', async () => {
    const mockList = {
      messages: [{ id: 'msg-1', conversation_id: 'conv-1', role: 'user', content: 'hello', input_tokens: 0, output_tokens: 0, model: '', created_at: '' }],
      total: 1,
    }
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockList)

    await useChatStore.getState().setCurrentConversation('conv-1')

    expect(useChatStore.getState().currentConversationId).toBe('conv-1')
    expect(apiClient.get).toHaveBeenCalledWith('/chat/conversations/conv-1/messages')
    expect(useChatStore.getState().messages).toEqual(mockList.messages)
  })

  it('sends message and handles stream fetch failures gracefully', async () => {
    useChatStore.setState({ currentConversationId: 'conv-1' })
    
    // Mock global fetch to return an error response
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Failed to stream' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await useChatStore.getState().sendMessage('Hello AI')

    expect(mockFetch).toHaveBeenCalled()
    expect(useChatStore.getState().isStreaming).toBe(false)
    expect(useChatStore.getState().streamError).toBe('Failed to stream')
  })
})
