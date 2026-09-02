<script setup>
import { ref, watch, computed, onBeforeUnmount } from 'vue'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'recognized'])

const {
  isSupported,
  isRecording,
  finalTranscript,
  interimTranscript,
  startRecording,
  stopRecording,
  cancelRecording,
  resetUI
} = useSpeechRecognition()

const statusText = ref('')
const statusType = ref('') // '' | 'error' | 'success'
const timerSeconds = ref(0)
let timerInterval = null
let maxTimer = null

const isOpen = computed(() => props.modelValue)
const displayText = computed(() => finalTranscript.value + interimTranscript.value)
const timerDisplay = computed(() => {
  const m = String(Math.floor(timerSeconds.value / 60)).padStart(2, '0')
  const s = String(timerSeconds.value % 60).padStart(2, '0')
  return `${m}:${s}`
})

watch(isOpen, (val) => {
  if (val) {
    statusText.value = ''
    statusType.value = ''
    timerSeconds.value = 0
    resetUI()
  } else {
    cleanup()
  }
})

function cleanup() {
  clearInterval(timerInterval)
  clearTimeout(maxTimer)
  timerInterval = null
  maxTimer = null
  if (isRecording.value) {
    cancelRecording()
  }
}

function handleStart() {
  statusText.value = ''
  statusType.value = ''
  timerSeconds.value = 0
  resetUI()
  startRecording()
  timerInterval = setInterval(() => { timerSeconds.value++ }, 1000)
  maxTimer = setTimeout(() => handleStop(), 60000)
}

function handleStop() {
  clearInterval(timerInterval)
  clearTimeout(maxTimer)
  stopRecording()
  // 延迟读取最终结果
  setTimeout(() => {
    const text = finalTranscript.value.trim()
    if (text) {
      statusText.value = '识别成功！'
      statusType.value = 'success'
      emit('recognized', text)
      setTimeout(() => close(), 1200)
    } else {
      statusText.value = '未识别到语音内容，请重试'
      statusType.value = 'error'
      setTimeout(() => close(), 2000)
    }
  }, 500)
}

function handleCancel() {
  cancelRecording()
  clearInterval(timerInterval)
  clearTimeout(maxTimer)
  close()
}

function close() {
  emit('update:modelValue', false)
}

onBeforeUnmount(() => {
  cleanup()
})
</script>

<template>
  <div class="voice-modal" :class="{ active: isOpen }" @click.self="handleCancel">
    <div class="voice-modal-card">
      <div class="voice-modal-title">
        <i class="fas fa-microphone"></i>
        语音输入
      </div>

      <div class="voice-recognition-area">
        <!-- 浏览器不支持 -->
        <div v-if="!isSupported" class="voice-unsupported">
          <i class="fas fa-exclamation-triangle"></i>
          <p>您的浏览器不支持语音识别功能</p>
          <p class="hint">请使用 Chrome、Edge 或 Safari 浏览器</p>
        </div>

        <!-- 录音中 UI -->
        <template v-else>
          <div v-if="isRecording" class="wave-container">
            <div class="wave-bar" v-for="i in 7" :key="i" :style="{ animationDelay: `${i * 0.1}s` }"></div>
          </div>

          <div v-if="isRecording" class="voice-timer">{{ timerDisplay }}</div>

          <div class="voice-text-display">
            <template v-if="displayText">
              {{ finalTranscript }}<span class="interim">{{ interimTranscript }}</span>
            </template>
            <span v-else class="placeholder">
              {{ isRecording ? '正在聆听...' : '点击麦克风按钮开始录音' }}
            </span>
          </div>
        </template>
      </div>

      <div class="voice-controls">
        <button class="voice-control-btn cancel" @click="handleCancel" title="取消">
          <i class="fas fa-times"></i>
        </button>
        <button
          v-if="!isRecording"
          class="voice-control-btn start"
          @click="handleStart"
          :disabled="!isSupported"
          title="开始录音"
        >
          <i class="fas fa-microphone"></i>
        </button>
        <button
          v-else
          class="voice-control-btn stop"
          @click="handleStop"
          title="停止录音"
        >
          <i class="fas fa-stop"></i>
        </button>
      </div>

      <div v-if="statusText" class="voice-status-text" :class="statusType">
        {{ statusText }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.voice-modal {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 1000;
  align-items: center;
  justify-content: center;
}

.voice-modal.active {
  display: flex;
}

.voice-modal-card {
  background: #1a1a1a;
  border: 1px solid #3d3a39;
  border-radius: 8px;
  padding: 24px;
  width: 400px;
  max-width: 90vw;
  text-align: center;
}

.voice-modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #f2f2f2;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.voice-recognition-area {
  min-height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.voice-unsupported {
  color: #bdbdbd;
}

.voice-unsupported i {
  font-size: 32px;
  color: #ff6b6b;
  margin-bottom: 12px;
}

.voice-unsupported .hint {
  font-size: 12px;
  color: #8b949e;
  margin-top: 4px;
}

.wave-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 40px;
  margin-bottom: 12px;
}

.wave-bar {
  width: 4px;
  height: 20px;
  background: #00d992;
  border-radius: 2px;
  animation: wave 0.8s ease-in-out infinite alternate;
}

@keyframes wave {
  from { height: 8px; }
  to { height: 32px; }
}

.voice-timer {
  font-family: 'SF Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 24px;
  color: #f2f2f2;
  margin-bottom: 12px;
}

.voice-text-display {
  font-size: 14px;
  color: #f2f2f2;
  line-height: 1.6;
  min-height: 24px;
  max-height: 100px;
  overflow-y: auto;
  word-break: break-word;
}

.voice-text-display .placeholder {
  color: #8b949e;
}

.voice-text-display .interim {
  font-style: italic;
  color: #bdbdbd;
}

.voice-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.voice-control-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 1px solid #3d3a39;
  background: #101010;
  color: #f2f2f2;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.voice-control-btn:hover {
  border-color: #00d992;
  color: #00d992;
}

.voice-control-btn.start {
  background: #00d992;
  color: #101010;
  border-color: #00d992;
}

.voice-control-btn.start:hover {
  background: #2fd6a1;
}

.voice-control-btn.start:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.voice-control-btn.stop {
  background: #ff6b6b;
  color: #fff;
  border-color: #ff6b6b;
}

.voice-control-btn.stop:hover {
  background: #ff5252;
}

.voice-status-text {
  margin-top: 16px;
  font-size: 13px;
  color: #bdbdbd;
}

.voice-status-text.error {
  color: #ff6b6b;
}

.voice-status-text.success {
  color: #00d992;
}
</style>
