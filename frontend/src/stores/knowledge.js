import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../api/index.js'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const documents = ref([])
  const total = ref(0)
  const sections = ref({})
  const currentFilter = ref('')
  const loading = ref(false)

  async function loadDocuments() {
    loading.value = true
    try {
      const res = await api.getKbDocuments()
      if (res.success) {
        documents.value = res.documents || []
        total.value = res.total || 0
        sections.value = res.sections || {}
      }
    } catch (e) {
      console.error('加载知识库文档失败:', e)
    } finally {
      loading.value = false
    }
  }

  async function addDocument(question, answer, section) {
    try {
      const res = await api.addKbDocument(question, answer, section)
      if (res.success !== false) {
        await loadDocuments()
      }
      return res
    } catch (e) {
      console.error('添加知识库文档失败:', e)
      return { success: false, message: '添加失败' }
    }
  }

  async function deleteDocument(docId) {
    try {
      const res = await api.deleteKbDocument(docId)
      if (res.success !== false) {
        await loadDocuments()
      }
      return res
    } catch (e) {
      console.error('删除知识库文档失败:', e)
      return { success: false, message: '删除失败' }
    }
  }

  return {
    documents,
    total,
    sections,
    currentFilter,
    loading,
    loadDocuments,
    addDocument,
    deleteDocument
  }
})
