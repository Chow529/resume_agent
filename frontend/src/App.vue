<script setup>
import { ref, watch, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import { useSessionStore } from '@/stores/session.js'
import { useChatStore } from '@/stores/chat.js'

import Sidebar from '@/components/Sidebar.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import AuthModal from '@/components/AuthModal.vue'
import HelpModal from '@/components/HelpModal.vue'
import UserManageModal from '@/components/UserManageModal.vue'
import UploadResumeModal from '@/components/UploadResumeModal.vue'
import ManageResumeModal from '@/components/ManageResumeModal.vue'
import KbModal from '@/components/KbModal.vue'

const authStore = useAuthStore()
const sessionStore = useSessionStore()
const chatStore = useChatStore()

// 模态框状态
const showAuth = ref(false)
const showHelp = ref(false)
const showUserManage = ref(false)
const showUploadResume = ref(false)
const showManageResume = ref(false)
const showKb = ref(false)

// 初始化：认证后加载会话，登出后重新弹出登录框
watch(() => authStore.isAuthenticated, async (val) => {
  if (val) {
    await sessionStore.initAndLoad()
  } else {
    showAuth.value = true
  }
})

onMounted(async () => {
  if (authStore.isAuthenticated) {
    await authStore.loadUserInfo()
    await sessionStore.initAndLoad()
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

function handleResumeUploaded() {
  chatStore.addMessage('assistant', '简历上传成功！您可以开始面试了。')
}
</script>

<template>
  <div class="layout">
    <Sidebar
      @open-upload-resume="openUploadResume"
      @open-manage-resume="openManageResume"
    />
    <ChatPanel
      @open-help="openHelp"
      @open-kb="openKb"
      @open-user-manage="openUserManage"
    />
  </div>

  <!-- 模态框 -->
  <AuthModal v-model="showAuth" />
  <HelpModal v-model="showHelp" />
  <UserManageModal v-model="showUserManage" />
  <UploadResumeModal v-model="showUploadResume" @uploaded="handleResumeUploaded" />
  <ManageResumeModal v-model="showManageResume" />
  <KbModal v-model="showKb" />
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
