<template>
  <aside class="sidebar">
    <!-- 品牌区 -->
    <div class="brand-section">
      <i class="fas fa-comment-dots brand-icon"></i>
      <h1 class="brand-title">面试模拟 Agent</h1>
      <p class="brand-subtitle">Web版 · 智能面试助手</p>
    </div>

    <!-- 会话状态卡 -->
    <div class="session-card">
      <span class="status-dot" :class="statusDotClass"></span>
      <span class="status-text">{{ statusText }}</span>
      <div v-if="sessionStore.currentDbSessionId" class="session-id">
        会话ID: {{ sessionStore.currentDbSessionId }}
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-actions">
      <div
        v-for="item in commandItems"
        :key="item.cmd"
        class="action-item"
        :class="{ disabled: !authStore.isAuthenticated }"
        @click="sendCommand(item.cmd)"
      >
        <i :class="item.icon"></i>
        <span>{{ item.label }}</span>
      </div>
      <div
        class="action-item"
        :class="{ disabled: !authStore.isAuthenticated }"
        id="uploadResumeBtn"
        @click="$emit('open-upload-resume')"
      >
        <i class="fas fa-upload"></i>
        <span>上传简历</span>
      </div>
      <div
        class="action-item"
        :class="{ disabled: !authStore.isAuthenticated }"
        id="manageResumeBtn"
        @click="$emit('open-manage-resume')"
      >
        <i class="fas fa-list"></i>
        <span>管理简历</span>
      </div>
    </div>

    <!-- 会话历史 -->
    <div v-if="authStore.isAuthenticated" class="session-history-list">
      <button class="btn btn-primary" style="width:100%;margin-bottom:12px;" :disabled="creating" @click="newSession">
        <i class="fas fa-plus"></i> {{ creating ? '创建中...' : '新对话' }}
      </button>
      <div
        v-for="s in sessionStore.sessionHistory"
        :key="s.id"
        class="session-history-item"
        :class="{ active: String(s.id) === String(sessionStore.currentDbSessionId) }"
        @click="loadSession(s)"
      >
        <div class="session-item-left">
          <i class="fas fa-comment"></i>
          <div class="session-item-info">
            <div class="session-item-name">{{ s.session_name || '未命名会话' }}</div>
          </div>
        </div>
        <div class="session-item-actions">
          <button class="action-btn" @click.stop="renameSession(s)" title="重命名">
            <i class="fas fa-pen"></i>
          </button>
          <button class="action-btn danger" @click.stop="deleteSession(s)" title="删除">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- 提示区 -->
    <div class="tips-section">
      <h3>使用提示</h3>
      <div class="tip-item">
        <i class="fas fa-lightbulb"></i>
        <span>输入 /start 开始面试流程</span>
      </div>
      <div class="tip-item">
        <i class="fas fa-lightbulb"></i>
        <span>上传简历后可进行针对性面试</span>
      </div>
      <div class="tip-item">
        <i class="fas fa-lightbulb"></i>
        <span>使用 /end 结束面试并获取评估</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import { useSessionStore } from '@/stores/session.js'
import { useChatStore } from '@/stores/chat.js'
import { useConfigStore } from '@/stores/config.js'
import { emit as busEmit } from '@/utils/events.js'

const props = defineProps({
  disabled: { type: Boolean, default: false }
})
const emit = defineEmits(['open-upload-resume', 'open-manage-resume'])

const authStore = useAuthStore()
const sessionStore = useSessionStore()
const chatStore = useChatStore()
const configStore = useConfigStore()

const creating = ref(false)

const commandItems = [
  { cmd: '/start', icon: 'fas fa-play', label: '开始面试' },
  { cmd: '/resume', icon: 'fas fa-file-alt', label: '查看简历' },
  { cmd: '/end', icon: 'fas fa-stop', label: '结束面试' },
]

const statusDotClass = computed(() => {
  const status = sessionStore.sessionStatus
  if (status === '已终止' || status === 'terminated') return 'terminated'
  if (status === '面试中' || status === 'interviewing') return 'interviewing'
  return ''
})

// 会话状态中文文案
const statusText = computed(() => {
  const map = {
    idle: '未开始面试',
    initialized: '未开始面试',
    interviewing: '面试中',
    terminated: '已终止'
  }
  return map[sessionStore.sessionStatus] || sessionStore.sessionStatus
})

function sendCommand(cmd) {
  if (!authStore.isAuthenticated || sessionStore.loading) return
  if (!configStore.configReady) {
    chatStore.addMessage('assistant', '⚠️ 请先完成 AI 模型配置后再使用该功能。[点击配置](open-config)')
    busEmit('open-config')
    return
  }
  chatStore.sendMessage(cmd)
}

async function newSession() {
  if (creating.value || sessionStore.loading) return
  if (!configStore.configReady) {
    busEmit('open-config')
    return
  }
  creating.value = true
  try {
    await sessionStore.createNewSession()
  } finally {
    creating.value = false
  }
}

async function loadSession(s) {
  await sessionStore.loadSessionMessages(s.id, s.session_name)
}

async function renameSession(s) {
  const newName = prompt('请输入新的会话名称', s.session_name || '未命名会话')
  if (newName) {
    await sessionStore.renameSession(s.id, newName)
  }
}

async function deleteSession(s) {
  if (sessionStore.sessionHistory.length <= 1) {
    alert('至少保留一条对话，无法删除')
    return
  }
  if (!confirm('确定要删除该会话吗？')) return
  const res = await sessionStore.deleteSession(s.id)
  if (res.success === false) {
    alert(res.message || '删除失败')
  }
}
</script>
