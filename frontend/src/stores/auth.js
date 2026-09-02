import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '../api/index.js'

export const useAuthStore = defineStore('auth', () => {
  const userId = ref(localStorage.getItem('agentUserId') || '')
  const username = ref('')
  const email = ref('')
  const isAuthenticated = computed(() => !!userId.value)
  const currentUserData = ref(null)

  // 获取 sessionId：优先隐藏字段 → URL 参数 → localStorage → 自动生成
  function getSessionId() {
    // 1. 隐藏 input 字段（模板注入的 {SESSION_ID}）
    const hiddenInput = document.getElementById('sessionIdInput')
    if (hiddenInput && hiddenInput.value && hiddenInput.value !== '{SESSION_ID}') {
      return hiddenInput.value
    }

    // 2. URL 参数
    const urlParams = new URLSearchParams(window.location.search)
    const urlSessionId = urlParams.get('session_id')
    if (urlSessionId) {
      localStorage.setItem('agentSessionId', urlSessionId)
      return urlSessionId
    }

    // 3. localStorage
    const stored = localStorage.getItem('agentSessionId')
    if (stored) return stored

    // 4. 自动生成
    const newId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9)
    localStorage.setItem('agentSessionId', newId)
    return newId
  }

  async function login(uname, password) {
    const res = await api.login(uname, password)
    if (res.success) {
      userId.value = res.userId
      username.value = uname
      localStorage.setItem('agentUserId', res.userId)
    }
    return res
  }

  async function register(uname, emailVal, password) {
    const res = await api.register(uname, emailVal, password)
    if (res.success) {
      userId.value = res.userId
      username.value = uname
      email.value = emailVal
      localStorage.setItem('agentUserId', res.userId)
    }
    return res
  }

  async function logout() {
    if (userId.value) {
      await api.logoutApi(userId.value).catch(() => {})
    }
    userId.value = ''
    username.value = ''
    email.value = ''
    currentUserData.value = null
    localStorage.removeItem('agentUserId')

    // 清理 session 和 chat 状态，防止重新登录时泄漏旧数据
    const { useSessionStore } = await import('./session.js')
    const { useChatStore } = await import('./chat.js')
    useSessionStore().reset()
    useChatStore().clearMessages()
  }

  async function checkAvailable(field, value) {
    return await api.checkAvailable(field, value)
  }

  async function loadUserInfo() {
    if (!userId.value) return null
    const res = await api.getUserInfo(userId.value)
    if (res.userId) {
      username.value = res.username || ''
      email.value = res.email || ''
      currentUserData.value = res
    }
    return res
  }

  async function updateEmailFn(newEmail) {
    const res = await api.updateEmail(userId.value, newEmail)
    if (res.success !== false) {
      email.value = newEmail
    }
    return res
  }

  async function updatePasswordFn(oldPassword, newPassword) {
    return await api.updatePassword(userId.value, oldPassword, newPassword)
  }

  return {
    userId,
    username,
    email,
    isAuthenticated,
    currentUserData,
    getSessionId,
    login,
    register,
    logout,
    checkAvailable,
    loadUserInfo,
    updateEmail: updateEmailFn,
    updatePassword: updatePasswordFn
  }
})
