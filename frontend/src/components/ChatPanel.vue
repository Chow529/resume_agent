<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat.js'
import { useAuthStore } from '@/stores/auth.js'
import { useSessionStore } from '@/stores/session.js'
import { useConfigStore } from '@/stores/config.js'
import { emit as busEmit } from '@/utils/events.js'
import MessageItem from './MessageItem.vue'
import VoiceModal from './VoiceModal.vue'

const emit = defineEmits(['open-help', 'open-kb', 'open-user-manage', 'open-model-config'])

const chatStore = useChatStore()
const authStore = useAuthStore()
const sessionStore = useSessionStore()
const configStore = useConfigStore()

const inputText = ref('')
const showVoiceModal = ref(false)
const messagesContainer = ref(null)
const textareaRef = ref(null)

const isAuthenticated = computed(() => authStore.isAuthenticated)
const messages = computed(() => chatStore.messages)
const isTyping = computed(() => chatStore.isTyping)
const statusText = computed(() => chatStore.statusText)
const sessionName = computed(() => {
  const current = sessionStore.sessionHistory.find(s => String(s.id) === String(sessionStore.currentDbSessionId))
  return current?.session_name || ''
})
const canSend = computed(() =>
  isAuthenticated.value &&
  inputText.value.trim() &&
  !isTyping.value &&
  !sessionStore.loading
)

// 状态点颜色
const statusDotClass = computed(() => {
  const status = sessionStore.sessionStatus
  if (status === 'idle') return 'dot-idle'
  if (status === 'interviewing') return 'dot-interviewing'
  return 'dot-default'
})

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(messages, () => scrollToBottom(), { deep: true })
watch(isTyping, () => scrollToBottom())
onMounted(() => scrollToBottom())

// 发送消息
function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return
  if (!configStore.configReady) {
    chatStore.addMessage('assistant', '⚠️ 请先完成 AI 模型配置后再使用该功能。[点击配置](open-config)')
    return
  }
  if (!canSend.value) return
  chatStore.sendMessage(text)
  inputText.value = ''
  resetTextareaHeight()
}

function openConfigModal() {
  busEmit('open-config')
}

// textarea 键盘处理
function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// textarea 自动调整高度
function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 100) + 'px'
}

function resetTextareaHeight() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
}

// 退出登录
function handleLogout() {
  if (confirm('确定要退出登录吗？')) {
    authStore.logout()
  }
}

// 语音识别结果回填
function handleVoiceRecognized(text) {
  inputText.value = text
  nextTick(() => autoResize())
}
</script>

<template>
  <div class="chat-panel">
    <!-- 顶部栏 -->
    <div class="top-bar">
      <div class="top-bar-left">
        <i class="fas fa-robot"></i>
        <span class="top-bar-title">{{ sessionName || '面试 Agent 对话' }}</span>
      </div>
      <div class="top-bar-right">
        <button
          v-if="isAuthenticated"
          class="top-bar-btn"
          @click="emit('open-user-manage')"
        >
          <i class="fas fa-user-cog"></i> 用户管理
        </button>
        <button
          v-if="isAuthenticated"
          class="top-bar-btn"
          @click="handleLogout"
        >
          <i class="fas fa-sign-out-alt"></i> 退出
        </button>
        <button
          class="top-bar-btn"
          @click="emit('open-model-config')"
          title="AI 模型配置"
        >
          <i class="fas fa-sliders-h"></i> 模型配置
        </button>
        <button
          class="top-bar-btn"
          :disabled="!isAuthenticated"
          @click="emit('open-kb')"
        >
          <i class="fas fa-database"></i> 知识库
        </button>
        <button
          class="top-bar-btn"
          :disabled="!isAuthenticated"
          @click="emit('open-help')"
        >
          <i class="fas fa-question-circle"></i> 帮助文档
        </button>
      </div>
    </div>

    <!-- AI 模型未配置警告 -->
    <div v-if="!configStore.configReady" class="config-warning">
      <i class="fas fa-exclamation-triangle"></i>
      <span>AI 模型尚未配置，无法使用对话功能。</span>
      <a href="#" @click.prevent="openConfigModal">立即配置 →</a>
    </div>

    <!-- 消息区域 -->
    <div class="chat-messages" ref="messagesContainer">
      <template v-if="messages.length === 0 && !isAuthenticated">
        <div class="empty-hint">
          <i class="fas fa-info-circle"></i>
          <p>请先登录或使用新用户注册...</p>
        </div>
      </template>
      <template v-else>
        <MessageItem
          v-for="(msg, idx) in messages"
          :key="idx"
          :role="msg.role"
          :content="msg.content"
        />
      </template>

      <!-- 输入指示器 -->
      <div v-if="isTyping" class="typing-indicator">
        <div class="typing-dots">
          <span></span><span></span><span></span>
        </div>
        <span class="typing-text">Agent 正在思考...</span>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        placeholder="输入消息... (Shift+Enter 换行, Enter 发送)"
        @keydown="handleKeydown"
        @input="autoResize"
        rows="1"
      ></textarea>
      <button
        class="input-btn voice-btn"
        :disabled="!isAuthenticated"
        @click="showVoiceModal = true"
        title="语音输入"
      >
        <i class="fas fa-microphone"></i>
      </button>
      <button
        class="input-btn send-btn"
        :class="{ disabled: !canSend }"
        :disabled="!canSend"
        @click="sendMessage"
      >
        <i class="fas fa-paper-plane"></i> 发送
      </button>
    </div>

    <!-- 状态栏 -->
    <div class="status-bar">
      <span class="status-dot" :class="statusDotClass"></span>
      <span class="status-text">{{ statusText }}</span>
    </div>

    <!-- 语音模态框 -->
    <VoiceModal
      v-model="showVoiceModal"
      @recognized="handleVoiceRecognized"
    />
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-canvas);
  color: var(--color-ink);
}

/* 顶部栏 */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-xl);
  border-bottom: 1px solid var(--color-hairline);
  flex-shrink: 0;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.top-bar-left i {
  color: var(--color-primary);
  font-size: 18px;
}

.top-bar-title {
  font-size: 16px;
  font-weight: 600;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.top-bar-btn {
  background: transparent;
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-sm);
  color: var(--color-ink);
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  transition: all 0.2s;
}

.top-bar-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.top-bar-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* AI 模型未配置警告 */
.config-warning {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-xl);
  background: rgba(251, 191, 36, 0.08);
  border-bottom: 1px solid rgba(251, 191, 36, 0.3);
  color: #fbbf24;
  font-size: 13px;
  flex-shrink: 0;
}

.config-warning i {
  flex-shrink: 0;
}

.config-warning a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
  margin-left: auto;
  white-space: nowrap;
}

.config-warning a:hover {
  text-decoration: underline;
}

/* 消息区域 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xl);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-mute);
  gap: var(--spacing-md);
}

.empty-hint i {
  font-size: 32px;
}

.empty-hint p {
  font-size: 14px;
}

/* 输入指示器 */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) 0;
}

.typing-dots {
  display: flex;
  gap: var(--spacing-xs);
}

.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: typingBounce 1.4s infinite ease-in-out both;
}

.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.typing-text {
  font-size: 12px;
  color: var(--color-mute);
}

/* 输入区域 */
.chat-input {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-top: 1px solid var(--color-hairline);
  flex-shrink: 0;
}

.chat-input textarea {
  flex: 1;
  background: var(--color-canvas-soft);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-sm);
  color: var(--color-ink);
  padding: var(--spacing-md) var(--spacing-lg);
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  outline: none;
  min-height: 44px;
  max-height: 120px;
  font-family: inherit;
  transition: border-color 0.15s;
}

.chat-input textarea:focus {
  border-color: var(--color-primary);
}

.chat-input textarea::placeholder {
  color: var(--color-mute);
}

.input-btn {
  background: transparent;
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-sm);
  color: var(--color-ink);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  transition: all 0.2s;
  flex-shrink: 0;
}

.voice-btn {
  width: 44px;
  height: 44px;
  font-size: 16px;
}

.voice-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.voice-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.send-btn {
  height: 44px;
  padding: 0 var(--spacing-lg);
  font-size: 14px;
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-on-primary);
  font-weight: 600;
}

.send-btn:hover:not(:disabled) {
  background: var(--color-primary-soft);
}

.send-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: var(--color-hairline);
  border-color: var(--color-hairline);
  color: var(--color-mute);
}

/* 状态栏 */
.status-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-xl);
  font-size: 12px;
  color: var(--color-mute);
  flex-shrink: 0;
  border-top: 1px solid var(--color-hairline);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-idle {
  background: var(--color-mute);
}

.dot-interviewing {
  background: #fbbf24;
  animation: pulse 1.5s infinite;
}

.dot-default {
  background: var(--color-primary);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
