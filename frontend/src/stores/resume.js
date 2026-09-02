import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from './auth.js'
import { useSessionStore } from './session.js'
import * as api from '../api/index.js'

export const useResumeStore = defineStore('resume', () => {
  const resumes = ref([])
  const loading = ref(false)

  async function uploadResume(file) {
    const authStore = useAuthStore()
    const sessionStore = useSessionStore()
    loading.value = true
    try {
      const res = await api.uploadResume(file, authStore.userId, sessionStore.sessionId)
      if (res.success !== false) {
        await loadResumes()
      }
      return res
    } catch (e) {
      console.error('上传简历失败:', e)
      return { success: false, message: '上传失败' }
    } finally {
      loading.value = false
    }
  }

  async function loadResumes() {
    const authStore = useAuthStore()
    if (!authStore.userId) return

    loading.value = true
    try {
      const res = await api.getResumeList(authStore.userId)
      if (res.success) {
        resumes.value = res.resumes || []
      }
    } catch (e) {
      console.error('加载简历列表失败:', e)
    } finally {
      loading.value = false
    }
  }

  async function activateResume(resumeId) {
    const sessionStore = useSessionStore()
    try {
      const res = await api.activateResume(resumeId, sessionStore.sessionId)
      return res
    } catch (e) {
      console.error('激活简历失败:', e)
      return { success: false, message: '激活失败' }
    }
  }

  async function deleteResumeFn(resumeId) {
    try {
      const res = await api.deleteResume(resumeId)
      if (res.success !== false) {
        await loadResumes()
      }
      return res
    } catch (e) {
      console.error('删除简历失败:', e)
      return { success: false, message: '删除失败' }
    }
  }

  return {
    resumes,
    loading,
    uploadResume,
    loadResumes,
    activateResume,
    deleteResume: deleteResumeFn
  }
})
