<script setup>
import { computed } from 'vue'
import { escapeHtml } from '@/utils/index.js'

const props = defineProps({
  role: { type: String, required: true, validator: v => ['user', 'assistant', 'agent'].includes(v) },
  content: { type: String, required: true }
})

const displayRole = computed(() => props.role === 'assistant' ? 'agent' : props.role)

const escapedContent = computed(() => escapeHtml(props.content))
</script>

<template>
  <div class="message" :class="displayRole">
    <div class="message-header">
      <i :class="displayRole === 'user' ? 'fas fa-user' : 'fas fa-robot'"></i>
      {{ displayRole === 'user' ? '你' : 'Agent' }}
    </div>
    <div class="message-content" v-html="escapedContent"></div>
  </div>
</template>

<style scoped>
.message {
  margin-bottom: var(--spacing-lg);
  animation: slideIn 0.3s ease-out;
}

.message.user {
  text-align: right;
}

.message.agent {
  text-align: left;
}

.message-header {
  font-size: 12px;
  color: var(--color-mute);
  margin-bottom: var(--spacing-xs);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.message.user .message-header {
  justify-content: flex-end;
}

.message.agent .message-header {
  justify-content: flex-start;
}

.message-content {
  display: inline-block;
  max-width: 80%;
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
  text-align: left;
}

.message.user .message-content {
  background: var(--color-primary);
  color: var(--color-on-primary);
  border-bottom-right-radius: 2px;
}

.message.agent .message-content {
  background: var(--color-canvas-soft);
  color: var(--color-ink);
  border: 1px solid var(--color-hairline);
  border-bottom-left-radius: 2px;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
