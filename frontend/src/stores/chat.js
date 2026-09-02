import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from './auth.js'
import { useSessionStore } from './session.js'
import * as api from '../api/index.js'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isTyping = ref(false)
  const statusText = ref('')

  function addMessage(role, content) {
    messages.value.push({ role, content })
  }

  async function sendMessage(message) {
    const authStore = useAuthStore()
    const sessionStore = useSessionStore()

    if (!message.trim()) return { success: false, message: '消息不能为空' }

    // 等待 session 初始化完成，避免 sessionId 为空
    await sessionStore.waitForReady()

    if (!sessionStore.sessionId) {
      return { success: false, message: '会话尚未初始化，请稍后重试' }
    }

    // 添加用户消息
    addMessage('user', message)
    isTyping.value = true
    statusText.value = 'AI 正在思考...'

    try {
      const res = await api.sendMessage(sessionStore.sessionId, message, authStore.userId)

      // 同步 db_session_id
      if (res.db_session_id && !sessionStore.currentDbSessionId) {
        const id = String(res.db_session_id)
        sessionStore.currentDbSessionId = id
        sessionStore.sessionId = id.startsWith('sess_') ? id : 'sess_' + id
      }

      // 处理响应类型
      if (res.type === 'interview_start') {
        sessionStore.sessionStatus = 'interviewing'
      } else if (res.type === 'interview_end') {
        sessionStore.sessionStatus = 'terminated'
      }

      // 添加 AI 回复
      if (res.message) {
        addMessage('assistant', res.message)
      }

      isTyping.value = false
      statusText.value = ''
      return res
    } catch (e) {
      isTyping.value = false
      statusText.value = ''
      addMessage('assistant', '抱歉，发生了一些错误，请重试。')
      return { success: false, message: e.message }
    }
  }

  function clearMessages() {
    messages.value = []
    isTyping.value = false
    statusText.value = ''
  }

  function addWelcomeMessage() {
    if (messages.value.length === 0) {
      addMessage('assistant', '你好！我是你的 AI 面试助手。请上传你的简历，或者直接开始面试对话。')
    }
  }

  return {
    messages,
    isTyping,
    statusText,
    addMessage,
    sendMessage,
    clearMessages,
    addWelcomeMessage
  }
})
