<template>
  <div>
    <!-- 主弹窗 -->
    <div class="modal-overlay" :class="{ active: modelValue }" @click.self="close">
      <div class="modal" style="max-width: 700px;">
        <div class="modal-header">
          <h3>知识库管理</h3>
          <button class="modal-close" @click="close">&times;</button>
        </div>
        <div class="modal-body">
          <!-- 统计栏 -->
          <div class="kb-stats">
            <div class="kb-stat-card">
              <div class="stat-value">{{ stats.docCount }}</div>
              <div class="stat-label">文档数</div>
            </div>
            <div class="kb-stat-card">
              <div class="stat-value">{{ stats.sectionCount }}</div>
              <div class="stat-label">分类数</div>
            </div>
            <div class="kb-stat-card">
              <div class="stat-value">{{ stats.lastUpdate || '--' }}</div>
              <div class="stat-label">最后更新</div>
            </div>
          </div>

          <!-- 分类筛选 -->
          <div class="kb-section-bar">
            <span
              class="kb-section-tag"
              :class="{ active: activeSection === '' }"
              @click="activeSection = ''"
            >全部 ({{ docs.length }})</span>
            <span
              v-for="sec in sectionList"
              :key="sec.name"
              class="kb-section-tag"
              :class="{ active: activeSection === sec.name }"
              @click="activeSection = sec.name"
            >{{ sec.name }} ({{ sec.count }})</span>
          </div>

          <!-- 搜索 -->
          <div class="kb-filter">
            <input
              v-model="searchText"
              type="text"
              placeholder="搜索文档内容..."
            />
          </div>

          <!-- 文档列表 -->
          <div v-if="kbLoading" class="kb-loading">
            <i class="fas fa-spinner fa-spin"></i> 加载中...
          </div>
          <div v-else class="kb-doc-list">
            <div v-if="!filteredDocs.length" style="text-align: center; padding: 16px; color: var(--color-mute); font-size: 13px;">
              暂无文档
            </div>
            <div
              v-for="doc in filteredDocs"
              :key="doc.doc_id || doc.id"
              class="kb-doc-item"
            >
              <div class="kb-doc-info">
                <div class="doc-id">{{ doc.doc_id || doc.id }}</div>
                <div class="doc-preview">{{ getPreview(doc.page_content) }}</div>
                <div class="doc-section">{{ doc.metadata?.section || doc.section || '' }}</div>
              </div>
              <div class="kb-doc-actions">
                <button title="查看" @click="viewDoc(doc)"><i class="fas fa-eye"></i></button>
                <button class="delete" title="删除" @click="confirmDelete(doc)"><i class="fas fa-trash"></i></button>
              </div>
            </div>
          </div>

          <!-- 新增文档表单 -->
          <div class="kb-form">
            <h4>新增 QA 文档</h4>
            <div class="kb-format-hint">格式示例：
Q: 如何注册账号？
A: 点击首页右上角"注册"按钮，填写手机号和密码即可完成注册。</div>

            <div class="kb-form-group">
              <label>分类</label>
              <select v-model="newDoc.section">
                <option value="系统概览">系统概览</option>
                <option value="注册与登录">注册与登录</option>
                <option value="简历管理">简历管理</option>
                <option value="面试功能">面试功能</option>
                <option value="语音功能">语音功能</option>
                <option value="常见问题">常见问题</option>
                <option value="自定义">自定义</option>
              </select>
            </div>

            <div class="kb-form-group">
              <label>问题 *</label>
              <textarea v-model="newDoc.question" placeholder="输入问题内容（至少 2 个字符）"></textarea>
              <div v-if="formErrors.question" class="field-error">{{ formErrors.question }}</div>
            </div>

            <div class="kb-form-group">
              <label>答案 *</label>
              <textarea v-model="newDoc.answer" placeholder="输入答案内容（至少 2 个字符）"></textarea>
              <div v-if="formErrors.answer" class="field-error">{{ formErrors.answer }}</div>
            </div>

            <div class="kb-form-actions">
              <button class="kb-btn" @click="clearForm">清空</button>
              <button
                class="kb-btn primary"
                :disabled="submitting"
                @click="submitDoc"
              >
                <template v-if="submitting">
                  <i class="fas fa-spinner fa-spin"></i> 提交中...
                </template>
                <template v-else>添加到知识库</template>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 文档详情子弹窗 -->
    <div v-if="viewingDoc" class="kb-detail-modal" @click.self="viewingDoc = null">
      <div class="kb-detail-card">
        <h4>{{ viewingDoc.doc_id || viewingDoc.id }}
          <span v-if="viewingDoc.metadata?.section || viewingDoc.section" style="font-weight: 400; font-size: 13px; color: var(--color-mute); margin-left: 8px;">
            {{ viewingDoc.metadata?.section || viewingDoc.section }}
          </span>
        </h4>
        <div class="detail-content">{{ viewingDoc.page_content }}</div>
        <div class="detail-close">
          <button class="kb-btn" @click="viewingDoc = null">关闭</button>
        </div>
      </div>
    </div>

    <!-- 删除确认 -->
    <div v-if="deleteTarget" class="kb-detail-modal" @click.self="deleteTarget = null">
      <div class="kb-detail-card" style="max-width: 400px;">
        <h4>确认删除</h4>
        <p style="color: var(--color-body); font-size: 14px;">
          确定要删除文档 <strong style="color: var(--color-primary);">{{ deleteTarget.doc_id || deleteTarget.id }}</strong> 吗？
        </p>
        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px;">
          <button class="kb-btn" @click="deleteTarget = null">取消</button>
          <button class="kb-btn primary" style="background: #e74c3c; border-color: #e74c3c;" @click="handleDelete">删除</button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast.show" class="kb-toast" :class="toast.type">
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, reactive, onUnmounted } from 'vue'
import { useKnowledgeStore } from '@/stores/knowledge.js'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const kbStore = useKnowledgeStore()

const kbLoading = ref(false)
const activeSection = ref('')
const searchText = ref('')
const viewingDoc = ref(null)
const deleteTarget = ref(null)
const submitting = ref(false)

const newDoc = reactive({
  section: '系统概览',
  question: '',
  answer: ''
})

const formErrors = reactive({
  question: '',
  answer: ''
})

const toast = reactive({
  show: false,
  message: '',
  type: 'success',
  _timer: null
})

function showToast(message, type = 'success') {
  if (toast._timer) clearTimeout(toast._timer)
  toast.message = message
  toast.type = type
  toast.show = true
  toast._timer = setTimeout(() => {
    toast.show = false
  }, 2500)
}

onUnmounted(() => {
  if (toast._timer) clearTimeout(toast._timer)
})

const docs = computed(() => kbStore.documents || [])

const stats = computed(() => {
  const allDocs = docs.value
  const sections = new Set()
  let lastUpdate = ''
  for (const doc of allDocs) {
    const sec = doc.metadata?.section || doc.section
    if (sec) sections.add(sec)
    const ts = doc.metadata?.updated_at || doc.updated_at
    if (ts && (!lastUpdate || ts > lastUpdate)) lastUpdate = ts
  }
  return {
    docCount: allDocs.length,
    sectionCount: sections.size,
    lastUpdate: lastUpdate ? formatTime(lastUpdate) : '--'
  }
})

const sectionList = computed(() => {
  const map = {}
  for (const doc of docs.value) {
    const sec = doc.metadata?.section || doc.section || '未分类'
    map[sec] = (map[sec] || 0) + 1
  }
  return Object.entries(map).map(([name, count]) => ({ name, count }))
})

const filteredDocs = computed(() => {
  let list = docs.value
  if (activeSection.value) {
    list = list.filter(d => (d.metadata?.section || d.section) === activeSection.value)
  }
  if (searchText.value.trim()) {
    const q = searchText.value.trim().toLowerCase()
    list = list.filter(d => (d.page_content || '').toLowerCase().includes(q))
  }
  return list
})

function getPreview(content) {
  if (!content) return ''
  const stripped = content.replace(/\*\*/g, '')
  return stripped.length > 100 ? stripped.slice(0, 100) + '...' : stripped
}

function formatTime(ts) {
  if (!ts) return '--'
  const d = new Date(typeof ts === 'number' ? ts * 1000 : ts)
  return d.toLocaleDateString('zh-CN')
}

function viewDoc(doc) {
  viewingDoc.value = doc
}

function confirmDelete(doc) {
  deleteTarget.value = doc
}

async function handleDelete() {
  if (!deleteTarget.value) return
  try {
    const id = deleteTarget.value.doc_id || deleteTarget.value.id
    await kbStore.deleteDocument(id)
    showToast('文档已删除')
  } catch (e) {
    showToast(e?.message || '删除失败', 'error')
  }
  deleteTarget.value = null
}

function clearForm() {
  newDoc.question = ''
  newDoc.answer = ''
  formErrors.question = ''
  formErrors.answer = ''
}

function validateForm() {
  let valid = true
  formErrors.question = ''
  formErrors.answer = ''

  if (!newDoc.question || newDoc.question.trim().length < 2) {
    formErrors.question = '问题至少需要 2 个字符'
    valid = false
  }
  if (!newDoc.answer || newDoc.answer.trim().length < 2) {
    formErrors.answer = '答案至少需要 2 个字符'
    valid = false
  }
  return valid
}

async function submitDoc() {
  if (!validateForm()) return

  submitting.value = true
  try {
    await kbStore.addDocument(newDoc.question.trim(), newDoc.answer.trim(), newDoc.section)
    showToast('文档已添加')
    clearForm()
  } catch (e) {
    showToast(e?.message || '添加失败', 'error')
  } finally {
    submitting.value = false
  }
}

function close() {
  emit('update:modelValue', false)
}

watch(() => props.modelValue, async (val) => {
  if (val) {
    kbLoading.value = true
    try {
      await kbStore.loadDocuments()
    } catch (e) {
      showToast('加载知识库失败', 'error')
    }
    kbLoading.value = false
  }
})
</script>
