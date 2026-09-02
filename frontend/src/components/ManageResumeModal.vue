<template>
  <div class="modal-overlay" :class="{ active: modelValue }" @click.self="close">
    <div class="modal">
      <div class="modal-header">
        <h3>管理简历</h3>
        <button class="modal-close" @click="close">&times;</button>
      </div>
      <div class="modal-body">
        <div v-if="loading" style="text-align: center; padding: 24px; color: var(--color-mute);">
          <i class="fas fa-spinner fa-spin"></i> 加载中...
        </div>
        <div v-else-if="!resumes.length" style="text-align: center; padding: 24px; color: var(--color-mute);">
          暂无简历，请先上传
        </div>
        <div v-else class="resume-list">
          <div
            v-for="resume in resumes"
            :key="resume.id"
            class="resume-card"
            :style="resume.is_active ? 'border-color: var(--color-primary)' : ''"
          >
            <div class="resume-info">
              <div class="resume-name">
                <span
                  class="resume-dot"
                  :style="{ background: resume.is_active ? 'var(--color-primary)' : '#555' }"
                ></span>
                {{ resume.filename }}
              </div>
              <div class="resume-time">
                {{ formatTime(resume.uploaded_at) }}
              </div>
            </div>
            <div class="resume-actions">
              <span
                v-if="resume.is_active"
                class="badge-active"
              >使用中</span>
              <button
                v-else
                class="btn btn-outline"
                style="font-size: 12px; padding: 4px 12px;"
                @click="activate(resume.id)"
              >激活</button>
              <button
                class="btn"
                style="font-size: 12px; padding: 4px 12px; color: #e74c3c;"
                @click="confirmDelete(resume)"
              >
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- 删除确认 -->
        <div v-if="deleteTarget" class="confirm-overlay" @click.self="deleteTarget = null">
          <div class="confirm-box">
            <p>确认删除 <strong>{{ deleteTarget.filename }}</strong>？</p>
            <div class="confirm-actions">
              <button class="btn btn-outline" @click="deleteTarget = null">取消</button>
              <button class="btn" style="background: #e74c3c; color: #fff;" @click="handleDelete">删除</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useResumeStore } from '@/stores/resume.js'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const resumeStore = useResumeStore()
const loading = ref(false)
const deleteTarget = ref(null)

const resumes = computed(() => resumeStore.resumes || [])

function close() {
  emit('update:modelValue', false)
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(typeof ts === 'number' ? ts * 1000 : ts)
  return d.toLocaleString('zh-CN')
}

async function activate(id) {
  try {
    await resumeStore.activateResume(id)
  } catch (e) {
    console.error('激活简历失败:', e)
  }
}

function confirmDelete(resume) {
  deleteTarget.value = resume
}

async function handleDelete() {
  if (!deleteTarget.value) return
  try {
    await resumeStore.deleteResume(deleteTarget.value.id)
  } catch (e) {
    console.error('删除简历失败:', e)
  }
  deleteTarget.value = null
}

watch(() => props.modelValue, async (val) => {
  if (val) {
    loading.value = true
    try {
      await resumeStore.loadResumes()
    } catch (e) {
      console.error('加载简历列表失败:', e)
    }
    loading.value = false
  }
})
</script>

<style scoped>
.resume-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.resume-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  background: var(--color-canvas-soft);
}
.resume-info {
  flex: 1;
  min-width: 0;
}
.resume-name {
  font-size: 14px;
  color: var(--color-ink);
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.resume-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.resume-time {
  font-size: 12px;
  color: var(--color-mute);
  margin-top: 4px;
  padding-left: 16px;
}
.resume-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.badge-active {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: var(--radius-pill);
  background: rgba(0, 217, 146, 0.15);
  color: var(--color-primary);
}
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
}
.confirm-box {
  background: var(--color-canvas-soft);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  padding: 24px;
  min-width: 300px;
}
.confirm-box p {
  margin: 0 0 16px;
  color: var(--color-ink);
}
.confirm-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
