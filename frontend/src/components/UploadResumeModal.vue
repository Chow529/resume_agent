<template>
  <div class="modal-overlay" :class="{ active: modelValue }" @click.self="close">
    <div class="modal">
      <div class="modal-header">
        <h3>上传简历</h3>
        <button class="modal-close" @click="close">&times;</button>
      </div>
      <div class="modal-body">
        <p style="color: var(--color-body); margin-bottom: 16px; font-size: 14px;">
          支持 PDF 和 DOCX 格式，每个用户最多保存 3 份简历
        </p>
        <div class="form-group">
          <label class="form-label">选择文件</label>
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf,.docx"
            class="form-input"
            @change="onFileChange"
          />
        </div>
        <div
          v-if="errorMessage"
          class="error-message"
          :class="{ show: !!errorMessage }"
        >
          {{ errorMessage }}
        </div>
        <div class="form-actions">
          <button
            class="btn btn-primary"
            :disabled="uploading"
            @click="handleUpload"
          >
            <template v-if="uploading">
              <i class="fas fa-spinner fa-spin"></i> 上传中...
            </template>
            <template v-else>
              <i class="fas fa-upload"></i> 上传
            </template>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useResumeStore } from '@/stores/resume.js'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue', 'uploaded'])

const resumeStore = useResumeStore()

const fileInputRef = ref(null)
const selectedFile = ref(null)
const errorMessage = ref('')
const uploading = ref(false)

function close() {
  emit('update:modelValue', false)
  resetForm()
}

function resetForm() {
  selectedFile.value = null
  errorMessage.value = ''
  uploading.value = false
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

function onFileChange(e) {
  const file = e.target.files[0]
  errorMessage.value = ''

  if (!file) {
    selectedFile.value = null
    return
  }

  const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
  const ext = file.name.toLowerCase().split('.').pop()

  if (!['pdf', 'docx'].includes(ext) && !validTypes.includes(file.type)) {
    errorMessage.value = '仅支持 PDF 和 DOCX 格式'
    selectedFile.value = null
    e.target.value = ''
    return
  }

  if (file.size > 10 * 1024 * 1024) {
    errorMessage.value = '文件大小不能超过 10MB'
    selectedFile.value = null
    e.target.value = ''
    return
  }

  selectedFile.value = file
}

async function handleUpload() {
  if (!selectedFile.value) {
    errorMessage.value = '请先选择文件'
    return
  }

  uploading.value = true
  errorMessage.value = ''

  try {
    await resumeStore.uploadResume(selectedFile.value)
    emit('uploaded', selectedFile.value.name)
    close()
  } catch (err) {
    errorMessage.value = err?.response?.data?.detail || err?.message || '上传失败，请重试'
  } finally {
    uploading.value = false
  }
}

watch(() => props.modelValue, (val) => {
  if (!val) {
    resetForm()
  }
})
</script>
