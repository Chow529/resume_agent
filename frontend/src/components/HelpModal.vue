<template>
  <div class="modal-overlay" :class="{ active: modelValue }" @click.self="close">
    <div class="modal">
      <div class="modal-header">
        <h3>可用命令</h3>
        <button class="modal-close" @click="close">&times;</button>
      </div>
      <div class="modal-body">
        <div class="command-item">
          <code>/start</code>
          <p>开始面试流程</p>
        </div>
        <div class="command-item">
          <code>/end</code>
          <p>结束面试</p>
        </div>
        <div class="command-item">
          <code>/resume</code>
          <p>查看简历内容</p>
        </div>
        <div class="command-item">
          <code>/vector 关键词</code>
          <p>查看向量库中相关JD数量</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

function close() {
  emit('update:modelValue', false)
}
</script>
