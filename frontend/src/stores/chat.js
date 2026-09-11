import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth.js'
import { useSessionStore } from './session.js'
import * as api from '../api/index.js'

export const useChatStore = defineStore('chat', () => {
  // 每个会话独立的消息列表缓存（按 sessionId 隔离）。
  // 这样切换会话时整体恢复对应会话的 messages，多会话同时推理时各自的 chunks
  // 都能正确追加到自己的 messages 末尾，互不干扰。
  const _messagesBySession = {}
  const messages = ref([])
  // 所有正在推理的会话 ID 集合（前端 sessionId）。
  // 用 Set 而非单值，支持多会话同时推理互不干扰：
  // 切换会话不会覆盖其他会话的推理状态，切回原会话时仍能接收剩余 chunks。
  const typingSessionIds = ref(new Set())
  const statusText = ref('')
  // 每个会话独立的 AbortController（按 sessionId 隔离），用于本地中止 fetch
  const _abortControllers = {}

  // isTyping：仅当当前会话正在推理时为 true
  const isTyping = computed(() => {
    const sessionStore = useSessionStore()
    return typingSessionIds.value.has(sessionStore.sessionId)
  })

  // 切换当前显示的会话：从缓存恢复该会话的 messages，缓存没有则保持空
  function switchToSession(sessionId) {
    if (!sessionId) {
      messages.value = []
      return
    }
    if (!_messagesBySession[sessionId]) {
      _messagesBySession[sessionId] = []
    }
    messages.value = _messagesBySession[sessionId]
  }

  // 把外部加载的会话消息（从数据库加载）覆盖到该会话的缓存
  function setSessionMessages(sessionId, msgs) {
    _messagesBySession[sessionId] = msgs
    // 如果当前显示的正是该会话，同步更新
    const sessionStore = useSessionStore()
    if (sessionStore.sessionId === sessionId) {
      messages.value = _messagesBySession[sessionId]
    }
  }

  function addMessage(role, content) {
    messages.value.push({ role, content })
  }

  // 追加 chunk 到指定会话的 messages 缓存中最后一条 assistant 消息。
  // 每个会话独立缓存，切换会话不影响其他会话的追加位置。
  function appendToLastAssistantOf(sessionId, delta) {
    const arr = _messagesBySession[sessionId]
    if (!arr) return
    for (let i = arr.length - 1; i >= 0; i--) {
      if (arr[i].role === 'assistant') {
        arr[i].content += delta
        return
      }
    }
    arr.push({ role: 'assistant', content: delta })
  }

  function setLastAssistantOf(sessionId, content) {
    const arr = _messagesBySession[sessionId]
    if (!arr) return
    for (let i = arr.length - 1; i >= 0; i--) {
      if (arr[i].role === 'assistant') {
        arr[i].content = content
        return
      }
    }
    arr.push({ role: 'assistant', content })
  }

  // 兼容旧调用：操作当前显示会话
  function appendToLastAssistant(delta) {
    const sessionStore = useSessionStore()
    appendToLastAssistantOf(sessionStore.sessionId, delta)
  }

  function setLastAssistant(content) {
    const sessionStore = useSessionStore()
    setLastAssistantOf(sessionStore.sessionId, content)
  }

  async function sendMessage(message, options = {}) {
    const authStore = useAuthStore()
    const sessionStore = useSessionStore()

    if (!message.trim()) return { success: false, message: '消息不能为空' }

    await sessionStore.waitForReady()

    if (!sessionStore.sessionId) {
      return { success: false, message: '会话尚未初始化，请稍后重试' }
    }

    const sentSessionId = sessionStore.sessionId
    const jdId = options.jdId ?? null

    // 确保该会话有独立的 messages 缓存，并切换为当前显示
    switchToSession(sentSessionId)

    // 添加用户消息（在 sentSessionId 对应的缓存中）
    _messagesBySession[sentSessionId].push({ role: 'user', content: message })
    // 紧接着追加一条空 assistant 消息，后续流式 chunk 都追加到这条
    _messagesBySession[sentSessionId].push({ role: 'assistant', content: '' })
    typingSessionIds.value.add(sentSessionId)
    // 触发响应式更新（Set 的 add 不会自动触发 computed 重算）
    typingSessionIds.value = new Set(typingSessionIds.value)
    statusText.value = 'AI 正在思考...'

    const { abortController, promise } = api.streamChat(sentSessionId, message, authStore.userId, {
      jdId,
      onChunk: (content) => {
        // 直接追加到 sentSessionId 对应的缓存，无论用户是否切换会话
        appendToLastAssistantOf(sentSessionId, content)
      },
      onDone: (data) => {
        // 同步 db_session_id（仅在尚未绑定时）
        if (data.db_session_id && !sessionStore.currentDbSessionId) {
          const id = String(data.db_session_id)
          sessionStore.currentDbSessionId = id
          sessionStore.sessionId = id.startsWith('sess_') ? id : 'sess_' + id
        }

        // 从推理集合中移除
        typingSessionIds.value.delete(sentSessionId)
        typingSessionIds.value = new Set(typingSessionIds.value)

        // 用最终的完整内容校准（防止流式累积遗漏）
        if (typeof data.content === 'string' && data.content) {
          setLastAssistantOf(sentSessionId, data.content)
        }

        // 只有当前仍停留在原会话时，才更新 sessionStatus
        if (sessionStore.sessionId === sentSessionId) {
          if (data.type === 'interview_start') {
            sessionStore.sessionStatus = 'interviewing'
          } else if (data.type === 'interview_end') {
            sessionStore.sessionStatus = 'terminated'
          }
        } else {
          // 用户已切换会话：刷新历史列表
          sessionStore.loadSessionHistory().catch(() => {})
        }

        if (typingSessionIds.value.size === 0) {
          statusText.value = ''
        }
      },
      onCancelled: (data) => {
        typingSessionIds.value.delete(sentSessionId)
        typingSessionIds.value = new Set(typingSessionIds.value)

        // 追加停止标记
        if (data.content) {
          setLastAssistantOf(sentSessionId, data.content)
        }
        // 移除可能存在的空 assistant 消息
        const arr = _messagesBySession[sentSessionId] || []
        const last = arr[arr.length - 1]
        if (last && last.role === 'assistant' && !last.content) {
          arr.pop()
        } else if (last && last.role === 'assistant' && last.content) {
          arr[arr.length - 1].content = last.content
        }
        if (typingSessionIds.value.size === 0) {
          statusText.value = ''
        }
      },
      onError: (data) => {
        typingSessionIds.value.delete(sentSessionId)
        typingSessionIds.value = new Set(typingSessionIds.value)
        const errMsg = data.message || '推理失败'
        setLastAssistantOf(sentSessionId, `⚠️ ${errMsg}`)
        if (typingSessionIds.value.size === 0) {
          statusText.value = ''
        }
      },
      onConfigRequired: (data) => {
        typingSessionIds.value.delete(sentSessionId)
        typingSessionIds.value = new Set(typingSessionIds.value)
        setLastAssistantOf(sentSessionId, data.message || '请先完成 AI 模型配置')
        if (typingSessionIds.value.size === 0) {
          statusText.value = ''
        }
      }
    })

    _abortControllers[sentSessionId] = abortController

    try {
      await promise
    } catch (e) {
      typingSessionIds.value.delete(sentSessionId)
      typingSessionIds.value = new Set(typingSessionIds.value)
      setLastAssistantOf(sentSessionId, `⚠️ ${e.message || '网络错误'}`)
      if (typingSessionIds.value.size === 0) {
        statusText.value = ''
      }
    } finally {
      delete _abortControllers[sentSessionId]
    }
  }

  // 取消当前会话正在进行的推理
  async function cancelChat() {
    const sessionStore = useSessionStore()
    const sid = sessionStore.sessionId
    if (!typingSessionIds.value.has(sid)) return
    // 通知后端取消
    await api.cancelChat(sid)
    // 本地中止 fetch（双保险）
    const ac = _abortControllers[sid]
    if (ac) {
      try { ac.abort() } catch {}
    }
    typingSessionIds.value.delete(sid)
    typingSessionIds.value = new Set(typingSessionIds.value)
    if (typingSessionIds.value.size === 0) {
      statusText.value = ''
    }
    // 把该会话最后一条 assistant 消息追加停止标记
    const arr = _messagesBySession[sid] || []
    if (arr.length > 0 && arr[arr.length - 1].role === 'assistant') {
      if (!arr[arr.length - 1].content) {
        arr.pop()
      } else {
        arr[arr.length - 1].content += '\n[已停止]'
      }
    }
  }

  function clearMessages() {
    // 清空当前显示的会话的 messages 缓存
    const sessionStore = useSessionStore()
    const sid = sessionStore.sessionId
    if (sid && _messagesBySession[sid]) {
      _messagesBySession[sid] = []
    }
    messages.value = []
    typingSessionIds.value = new Set()
    statusText.value = ''
    // 清理所有 abort controller
    for (const sid of Object.keys(_abortControllers)) {
      try { _abortControllers[sid].abort() } catch {}
      delete _abortControllers[sid]
    }
  }

  function addWelcomeMessage() {
    const sessionStore = useSessionStore()
    const sid = sessionStore.sessionId
    const arr = sid ? _messagesBySession[sid] : messages.value
    if (arr && arr.length === 0) {
      arr.push({ role: 'assistant', content: '你好！我是你的 AI 面试助手。请上传你的简历，或者直接开始面试对话。' })
    } else if (!arr) {
      messages.value.push({ role: 'assistant', content: '你好！我是你的 AI 面试助手。请上传你的简历，或者直接开始面试对话。' })
    }
  }

  return {
    messages,
    isTyping,
    typingSessionIds,
    statusText,
    addMessage,
    sendMessage,
    cancelChat,
    clearMessages,
    addWelcomeMessage,
    switchToSession,
    setSessionMessages
  }
})
