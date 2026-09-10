import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../api/index.js'

export const useConfigStore = defineStore('config', () => {
  const configReady = ref(false)

  async function checkConfig() {
    try {
      const res = await api.checkConfigStatus()
      configReady.value = res.success && res.ready
    } catch {
      configReady.value = false
    }
    return configReady.value
  }

  return { configReady, checkConfig }
})
