<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import { useSessionStore } from '@/stores/session.js'
import { useChatStore } from '@/stores/chat.js'
import { useConfigStore } from '@/stores/config.js'
import { on as busOn, off as busOff } from '@/utils/events.js'

import Sidebar from '@/components/Sidebar.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import AuthModal from '@/components/AuthModal.vue'
import HelpModal from '@/components/HelpModal.vue'
import UserManageModal from '@/components/UserManageModal.vue'
import UploadResumeModal from '@/components/UploadResumeModal.vue'
import ManageResumeModal from '@/components/ManageResumeModal.vue'
import KbModal from '@/components/KbModal.vue'
import ModelConfigModal from '@/components/ModelConfigModal.vue'
import DataCenterModal from '@/components/DataCenterModal.vue'
import JDSelectModal from '@/components/JDSelectModal.vue'

const authStore = useAuthStore()
const sessionStore = useSessionStore()
const chatStore = useChatStore()
const configStore = useConfigStore()

// 模态框状态
const showAuth = ref(false)
const showHelp = ref(false)
const showUserManage = ref(false)
const showUploadResume = ref(false)
const showManageResume = ref(false)
const showKb = ref(false)
const showModelConfig = ref(false)
const showDataCenter = ref(false)
const showJdSelect = ref(false)

function openModelConfig() {
  showModelConfig.value = true
}

// 监听全局事件：其他组件触发"打开配置"
busOn('open-config', openModelConfig)
onUnmounted(() => busOff('open-config', openModelConfig))

// 认证后：加载会话 + 检查配置，未配置时自动弹出配置页
watch(() => authStore.isAuthenticated, async (val) => {
  if (val) {
    await sessionStore.initAndLoad()
    const ready = await configStore.checkConfig()
    if (!ready) openModelConfig()
  } else {
    showAuth.value = true
  }
})

onMounted(async () => {
  if (authStore.isAuthenticated) {
    await authStore.loadUserInfo()
    await sessionStore.initAndLoad()
    const ready = await configStore.checkConfig()
    if (!ready) openModelConfig()
  } else {
    showAuth.value = true
  }
})

// ChatPanel 事件
function openHelp() {
  if (!authStore.isAuthenticated) return
  showHelp.value = true
}

function openKb() {
  if (!authStore.isAuthenticated) return
  showKb.value = true
}

function openUserManage() {
  if (!authStore.isAuthenticated) return
  showUserManage.value = true
}

// Sidebar 事件
function openUploadResume() {
  if (!authStore.isAuthenticated) return
  showUploadResume.value = true
}

function openManageResume() {
  if (!authStore.isAuthenticated) return
  showManageResume.value = true
}

// 数据中心（岗位 JD 采集）
function openDataCenter() {
  if (!authStore.isAuthenticated) return
  showDataCenter.value = true
}

// 开始面试：先选择目标岗位 JD（个人数据 / 公用数据）
function startInterview() {
  if (!authStore.isAuthenticated || sessionStore.loading) return
  if (!configStore.configReady) {
    chatStore.addMessage('assistant', '⚠️ 请先完成 AI 模型配置后再使用该功能。[点击配置](open-config)')
    openModelConfig()
    return
  }
  showJdSelect.value = true
}

// 选定 JD 后携带 jdId 发起 /start 面试
function handleJdSelected(jd) {
  chatStore.sendMessage('/start', { jdId: jd.id })
}

// 跳过选岗：不携带 jdId 发起 /start，走旧流程（Agent 通过工具从简历提取意向并查询岗位）
function handleJdSkip() {
  chatStore.sendMessage('/start')
}

function handleResumeUploaded() {
  chatStore.addMessage('assistant', '简历上传成功！您可以开始面试了。')
}

// 配置保存成功后刷新状态
function handleConfigSaved() {
  configStore.checkConfig()
}
</script>

<template>
  <div class="layout">
    <Sidebar
      @open-upload-resume="openUploadResume"
      @open-manage-resume="openManageResume"
      @open-data-center="openDataCenter"
      @start-interview="startInterview"
    />
    <ChatPanel
      @open-help="openHelp"
      @open-kb="openKb"
      @open-user-manage="openUserManage"
      @open-model-config="openModelConfig"
      @start-interview="startInterview"
    />
  </div>

  <!-- 模态框 -->
  <AuthModal v-model="showAuth" />
  <HelpModal v-model="showHelp" />
  <UserManageModal v-model="showUserManage" />
  <UploadResumeModal v-model="showUploadResume" @uploaded="handleResumeUploaded" />
  <ManageResumeModal v-model="showManageResume" />
  <KbModal v-model="showKb" />
  <ModelConfigModal v-model="showModelConfig" @saved="handleConfigSaved" />
  <JDSelectModal
    v-model="showJdSelect"
    :user-id="authStore.userId"
    @select="handleJdSelected"
    @skip="handleJdSkip"
    @open-data-center="openDataCenter"
  />
  <DataCenterModal v-model="showDataCenter" :user-id="authStore.userId" />
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  width: 100%;
}

.layout > :deep(.chat-panel) {
  flex: 1;
  min-width: 0;
}
</style>
