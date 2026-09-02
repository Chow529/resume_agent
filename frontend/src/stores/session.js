import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from './auth.js'
import * as api from '../api/index.js'

export const useSessionStore = defineStore('session', () => {
  const sessionId = ref('')          // 前端 sessionId
  const currentDbSessionId = ref('') // 数据库中的 session ID
  const sessionHistory = ref([])     // 会话列表
  const sessionStatus = ref('idle')  // 'idle' | 'interviewing' | 'terminated'
  const loading = ref(false)         // 初始化加载中标记
  let _initPromise = null            // 用于让其他操作等待初始化完成

  // 确保 sessionId 不带重复的 'sess_' 前缀
  function withSessPrefix(id) {
    const str = String(id)
    return str.startsWith('sess_') ? str : 'sess_' + str
  }

  // 认证后初始化：尝试加载最近 session，没有则创建新的
  async function initAndLoad() {
    const authStore = useAuthStore()
    if (!authStore.userId) return

    loading.value = true
    _initPromise = _doInitLoad()
    try {
      await _initPromise
    } finally {
      loading.value = false
      _initPromise = null
    }
  }

  async function _doInitLoad() {
    const authStore = useAuthStore()
    try {
      const res = await api.getLatestSession(authStore.userId)
      if (res.success && res.has_session && res.session) {
        await loadExistingSession({
          session: res.session,
          messages: res.messages || []
        })
      } else {
        await createNewSession()
      }
    } catch {
      await createNewSession()
    }
  }

  // 等待初始化完成（供 sendMessage 等使用）
  async function waitForReady() {
    if (_initPromise) await _initPromise
  }

  // 登出时重置所有状态
  function reset() {
    sessionId.value = ''
    currentDbSessionId.value = ''
    sessionHistory.value = []
    sessionStatus.value = 'idle'
    loading.value = false
    _initPromise = null
  }

  // 加载已有 session（带消息）
  async function loadExistingSession(data) {
    const authStore = useAuthStore()
    const dbId = data.session.id || data.session.db_session_id || data.session._id
    sessionId.value = withSessPrefix(dbId)
    currentDbSessionId.value = String(dbId)

    // init + bind
    await api.initSession(sessionId.value).catch(() => {})
    await api.bindUserToSession(sessionId.value, authStore.userId).catch(() => {})

    // 加载消息到 chat store（延迟导入避免循环依赖）
    const { useChatStore } = await import('./chat.js')
    const chatStore = useChatStore()
    if (data.messages && data.messages.length > 0) {
      chatStore.messages = data.messages.map(m => ({
        role: (m.role === 'agent' ? 'assistant' : (m.role || m.sender || 'user')),
        content: m.content || m.message
      }))
    } else {
      chatStore.addWelcomeMessage()
    }

    // 检查 session 状态
    await checkSession()

    // 刷新历史列表
    await loadSessionHistory()
  }

  // 创建新 session
  async function createNewSession() {
    const authStore = useAuthStore()

    // 先清空聊天
    const { useChatStore } = await import('./chat.js')
    const chatStore = useChatStore()
    chatStore.clearMessages()
    chatStore.addWelcomeMessage()

    // 清除旧的 sessionId，让 getSessionId 生成全新的 ID
    localStorage.removeItem('agentSessionId')
    // 生成前端 sessionId
    sessionId.value = authStore.getSessionId()
    currentDbSessionId.value = ''
    sessionStatus.value = 'idle'

    // init session（传 user_id 让后端直接创建 DB 记录）
    try {
      const initRes = await api.initSession(sessionId.value, authStore.userId)
      if (initRes.db_session_id) {
        currentDbSessionId.value = String(initRes.db_session_id)
        sessionId.value = withSessPrefix(initRes.db_session_id)
      }
    } catch {}

    // bind user — 兜底：若 init 未返回 db_session_id，bind 会创建并返回
    if (!currentDbSessionId.value) {
      try {
        const bindRes = await api.bindUserToSession(sessionId.value, authStore.userId)
        if (bindRes.db_session_id) {
          currentDbSessionId.value = String(bindRes.db_session_id)
          sessionId.value = withSessPrefix(bindRes.db_session_id)
        }
      } catch {}
    }

    await loadSessionHistory()
  }

  // 加载指定 session 的消息
  async function loadSessionMessages(dbSessionId, sessionName) {
    const authStore = useAuthStore()

    try {
      const res = await api.getSessionMessages(dbSessionId)
      if (res.success && res.messages) {
        sessionId.value = withSessPrefix(dbSessionId)
        currentDbSessionId.value = String(dbSessionId)

        // init + bind
        await api.initSession(sessionId.value).catch(() => {})
        await api.bindUserToSession(sessionId.value, authStore.userId).catch(() => {})

        const { useChatStore } = await import('./chat.js')
        const chatStore = useChatStore()
        chatStore.messages = res.messages.map(m => ({
          role: (m.role === 'agent' ? 'assistant' : (m.role || m.sender || 'user')),
          content: m.content || m.message
        }))

        await checkSession()
      }
    } catch (e) {
      console.error('加载会话消息失败:', e)
    }
  }

  // 加载会话历史列表
  async function loadSessionHistory() {
    const authStore = useAuthStore()
    if (!authStore.userId) return

    try {
      const res = await api.getSessionList(authStore.userId)
      if (res.success) {
        sessionHistory.value = res.sessions || []
      }
    } catch (e) {
      console.error('加载会话列表失败:', e)
    }
  }

  // 重命名 session
  async function renameSessionFn(dbSessionId, name) {
    try {
      const res = await api.renameSession(dbSessionId, name)
      if (res.success !== false) {
        await loadSessionHistory()
      }
      return res
    } catch (e) {
      console.error('重命名会话失败:', e)
      return { success: false, message: '重命名失败' }
    }
  }

  // 删除 session
  async function deleteSessionFn(dbSessionId) {
    try {
      const res = await api.deleteSession(dbSessionId)
      if (res.success !== false) {
        const isCurrent = String(currentDbSessionId.value) === String(dbSessionId)
        await loadSessionHistory()
        
        // 如果删除的是当前 session，切换到历史中的第一个会话，或创建新会话
        if (isCurrent) {
          if (sessionHistory.value.length > 0) {
            // 切换到第一个历史会话
            const first = sessionHistory.value[0]
            await loadSessionMessages(first.id, first.session_name)
          } else {
            await createNewSession()
          }
        }
      }
      return res
    } catch (e) {
      console.error('删除会话失败:', e)
      return { success: false, message: '删除失败' }
    }
  }

  // 检查 session 状态
  async function checkSession() {
    if (!sessionId.value) return
    try {
      const res = await api.getSessionStatus(sessionId.value)
      if (res.status) {
        sessionStatus.value = res.status
      }
    } catch {
      // 静默失败
    }
  }

  return {
    sessionId,
    currentDbSessionId,
    sessionHistory,
    sessionStatus,
    loading,
    initAndLoad,
    waitForReady,
    reset,
    loadExistingSession,
    createNewSession,
    loadSessionMessages,
    loadSessionHistory,
    renameSession: renameSessionFn,
    deleteSession: deleteSessionFn,
    checkSession
  }
})
