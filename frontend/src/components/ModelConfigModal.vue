<template>
  <div>
    <div class="modal-overlay" :class="{ active: modelValue }" @click.self="close">
      <div class="modal config-modal">
        <div class="modal-header">
          <h3>AI 模型配置</h3>
          <button class="modal-close" @click="close">&times;</button>
        </div>
        <div class="modal-body">
          <!-- 配置表单 -->
          <div class="config-form">
            <div class="form-row">
              <div class="form-group-half">
                <label>供应商</label>
                <select v-model="form.provider">
                  <option value="openai">OpenAI 兼容</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="deepseek">DeepSeek</option>
                </select>
              </div>
              <div class="form-group-half">
                <label>模型名称 *</label>
                <input v-model="form.model_name" type="text" placeholder="如 deepseek-chat" />
                <div v-if="errors.model_name" class="field-error">{{ errors.model_name }}</div>
              </div>
            </div>

            <div class="form-group">
              <label>API Key *</label>
              <div class="api-key-wrapper">
                <input
                  v-model="form.api_key"
                  :type="showApiKey ? 'text' : 'password'"
                  placeholder="输入 API Key"
                  class="api-key-input"
                />
                <button class="toggle-btn" @click="showApiKey = !showApiKey" type="button">
                  <i :class="showApiKey ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
                </button>
              </div>
              <div v-if="errors.api_key" class="field-error">{{ errors.api_key }}</div>
            </div>

            <div class="form-group">
              <label>Base URL *</label>
              <input v-model="form.base_url" type="text" placeholder="如 https://api.deepseek.com/v1" />
              <div v-if="errors.base_url" class="field-error">{{ errors.base_url }}</div>
            </div>

            <div class="form-row">
              <div class="form-group-half">
                <label>温度值 ({{ form.temperature }})</label>
                <div class="slider-row">
                  <input
                    v-model.number="form.temperature"
                    type="range"
                    min="0" max="2" step="0.1"
                    class="temp-slider"
                  />
                  <input
                    v-model.number="form.temperature"
                    type="number"
                    min="0" max="2" step="0.1"
                    class="temp-num"
                  />
                </div>
                <div v-if="errors.temperature" class="field-error">{{ errors.temperature }}</div>
              </div>
              <div class="form-group-half">
                <label>最大 Tokens</label>
                <input v-model.number="form.max_tokens" type="number" min="1" max="128000" placeholder="4096" />
                <div v-if="errors.max_tokens" class="field-error">{{ errors.max_tokens }}</div>
              </div>
            </div>

            <!-- Embedding 配置 -->
            <div class="embedding-section">
              <div class="embedding-toggle">
                <label class="switch-label">
                  <input type="checkbox" v-model="form.embedding_separate" />
                  <span class="switch-track"></span>
                  <span>向量模型使用独立配置</span>
                </label>
                <span class="switch-hint">当向量模型与主模型不属同一供应商时开启</span>
              </div>

              <!-- 共用主模型配置：只需填模型名 -->
              <div v-if="!form.embedding_separate" class="embedding-fields">
                <div class="form-group">
                  <label>Embedding 模型名称</label>
                  <input v-model="form.embedding_model" type="text" placeholder="如 text-embedding-3-small（使用主模型 API Key 和 Base URL）" />
                </div>
              </div>

              <!-- 独立配置：完整表单 -->
              <div v-if="form.embedding_separate" class="embedding-fields">
                <div class="form-row">
                  <div class="form-group-half">
                    <label>向量供应商</label>
                    <select v-model="form.embedding_provider">
                      <option value="openai">OpenAI 兼容</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="deepseek">DeepSeek</option>
                    </select>
                  </div>
                  <div class="form-group-half">
                    <label>向量模型名称</label>
                    <input v-model="form.embedding_model" type="text" placeholder="如 text-embedding-3-small" />
                  </div>
                </div>
                <div class="form-group">
                  <label>向量 API Key</label>
                  <div class="api-key-wrapper">
                    <input
                      v-model="form.embedding_api_key"
                      :type="showEmbApiKey ? 'text' : 'password'"
                      placeholder="向量模型 API Key"
                      class="api-key-input"
                    />
                    <button class="toggle-btn" @click="showEmbApiKey = !showEmbApiKey" type="button">
                      <i :class="showEmbApiKey ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
                    </button>
                  </div>
                </div>
                <div class="form-group">
                  <label>向量 Base URL</label>
                  <input v-model="form.embedding_base_url" type="text" placeholder="如 https://api.openai.com/v1" />
                </div>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="config-actions">
            <button class="cfg-btn" @click="handleReset" :disabled="saving">
              <i class="fas fa-undo"></i> 重置
            </button>
            <div class="config-actions-right">
              <button class="cfg-btn" @click="handleImport" :disabled="saving">
                <i class="fas fa-file-import"></i> 导入
              </button>
              <button class="cfg-btn primary" @click="handleSave" :disabled="saving || !hasChanges">
                <template v-if="saving">
                  <i class="fas fa-spinner fa-spin"></i> 保存中...
                </template>
                <template v-else>
                  <i class="fas fa-save"></i> 保存配置
                </template>
              </button>
            </div>
          </div>
          <input ref="importInput" type="file" accept=".json" style="display:none" @change="onFileSelected" />
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
import { ref, reactive, computed, watch, onUnmounted } from 'vue'
import { loadModelConfig, saveModelConfig, resetModelConfig } from '@/api/index.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'saved'])

const importInput = ref(null)
const showApiKey = ref(false)
const showEmbApiKey = ref(false)
const saving = ref(false)

const form = reactive({
  provider: 'openai',
  model_name: '',
  api_key: '',
  base_url: '',
  temperature: 0.7,
  max_tokens: 4096,
  embedding_model: '',
  embedding_separate: false,
  embedding_provider: 'openai',
  embedding_api_key: '',
  embedding_base_url: ''
})

// 保存初始表单状态，用于检测是否有修改
const initialForm = ref({ ...form })

// 计算是否有修改
const hasChanges = computed(() => {
  return Object.keys(form).some(key => form[key] !== initialForm.value[key])
})

const errors = reactive({
  model_name: '',
  api_key: '',
  base_url: '',
  temperature: '',
  max_tokens: ''
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
  toast._timer = setTimeout(() => { toast.show = false }, 2500)
}

onUnmounted(() => { if (toast._timer) clearTimeout(toast._timer) })

function clearErrors() {
  for (const k of Object.keys(errors)) errors[k] = ''
}

function validate() {
  clearErrors()
  let valid = true
  if (!form.model_name?.trim()) { errors.model_name = '模型名称不能为空'; valid = false }
  if (!form.api_key?.trim()) { errors.api_key = 'API Key 不能为空'; valid = false }
  if (!form.base_url?.trim()) { errors.base_url = 'Base URL 不能为空'; valid = false }
  const t = Number(form.temperature)
  if (isNaN(t) || t < 0 || t > 2) { errors.temperature = '温度值需在 0~2 之间'; valid = false }
  const m = Number(form.max_tokens)
  if (form.max_tokens !== '' && (isNaN(m) || m < 1)) { errors.max_tokens = '必须为正整数'; valid = false }
  return valid
}

async function loadConfig() {
  try {
    const res = await loadModelConfig()
    if (res.success && res.config) {
      const c = res.config
      form.provider = c.provider || 'openai'
      form.model_name = c.model_name || ''
      form.api_key = c.api_key || ''
      form.base_url = c.base_url || ''
      form.temperature = c.temperature ?? 0.7
      form.max_tokens = c.max_tokens ?? 4096
      form.embedding_model = c.embedding_model || ''
      form.embedding_separate = !!c.embedding_separate
      form.embedding_provider = c.embedding_provider || 'openai'
      form.embedding_api_key = c.embedding_api_key || ''
      form.embedding_base_url = c.embedding_base_url || ''
      // 保存初始状态
      initialForm.value = { ...form }
    }
  } catch (e) {
    console.error('加载配置失败', e)
  }
}

async function handleSave() {
  if (!validate()) return
  saving.value = true
  try {
    const res = await saveModelConfig({ ...form })
    if (res.success) {
      showToast('配置已保存，模型已重新加载')
      // 更新初始状态
      initialForm.value = { ...form }
      emit('saved')
    } else {
      showToast(res.message || '保存失败', 'error')
    }
  } catch (e) {
    showToast(e?.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function handleReset() {
  if (!confirm('确定要重置配置吗？重置后需重新填写 AI 模型配置。')) return
  try {
    const res = await resetModelConfig()
    if (res.success) {
      showToast('配置已重置')
      form.provider = 'openai'
      form.model_name = ''
      form.api_key = ''
      form.base_url = ''
      form.temperature = 0.7
      form.max_tokens = 4096
      form.embedding_model = ''
      form.embedding_separate = false
      form.embedding_provider = 'openai'
      form.embedding_api_key = ''
      form.embedding_base_url = ''
      // 更新初始状态
      initialForm.value = { ...form }
      clearErrors()
      emit('saved')
    } else {
      showToast(res.message || '重置失败', 'error')
    }
  } catch (e) {
    showToast(e?.message || '重置失败', 'error')
  }
}

function handleImport() {
  importInput.value?.click()
}

async function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const c = JSON.parse(text)
    form.provider = c.provider || 'openai'
    form.model_name = c.model_name || ''
    form.api_key = c.api_key || ''
    form.base_url = c.base_url || ''
    form.temperature = c.temperature ?? 0.7
    form.max_tokens = c.max_tokens ?? 4096
    form.embedding_model = c.embedding_model || ''
    form.embedding_separate = !!c.embedding_separate
    form.embedding_provider = c.embedding_provider || 'openai'
    form.embedding_api_key = c.embedding_api_key || ''
    form.embedding_base_url = c.embedding_base_url || ''
    // 更新初始状态
    initialForm.value = { ...form }
    clearErrors()
    showToast('配置已从文件导入')
  } catch (err) {
    showToast('文件格式错误，需为有效的 JSON 配置', 'error')
  }
  // 清空 input 以便重复选择同一文件
  if (importInput.value) importInput.value.value = ''
}

function close() {
  emit('update:modelValue', false)
}

watch(() => props.modelValue, async (val) => {
  if (val) {
    await loadConfig()
  }
})
</script>

<style scoped>
.config-modal {
  max-width: 640px;
}

/* 表单 */
.config-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.form-row {
  display: flex;
  gap: var(--spacing-md);
}

.form-group,
.form-group-half {
  display: flex;
  flex-direction: column;
}

.form-group-half {
  flex: 1;
}

.config-form label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-body);
  margin-bottom: var(--spacing-xs);
}

.config-form input[type="text"],
.config-form input[type="number"],
.config-form input[type="password"],
.config-form select {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-sm);
  color: var(--color-ink);
  font-size: 13px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s;
}

.config-form input:focus,
.config-form select:focus {
  border-color: var(--color-primary);
}

.config-form input::placeholder {
  color: var(--color-mute);
}

.config-form select {
  cursor: pointer;
}

/* API Key 展示/隐藏 */
.api-key-wrapper {
  display: flex;
  gap: 0;
}

.api-key-input {
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
  flex: 1;
}

.toggle-btn {
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-left: none;
  border-top-right-radius: var(--radius-sm);
  border-bottom-right-radius: var(--radius-sm);
  color: var(--color-mute);
  cursor: pointer;
  padding: 0 var(--spacing-md);
  font-size: 14px;
  transition: color 0.15s, border-color 0.15s;
}

.toggle-btn:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

/* 温度滑块 */
.slider-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.temp-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  background: var(--color-hairline);
  border-radius: 2px;
  outline: none;
}

.temp-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-primary);
  cursor: pointer;
  border: 2px solid var(--color-canvas);
}

.temp-num {
  width: 64px !important;
  text-align: center;
  font-family: 'SF Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}

.field-error {
  font-size: 12px;
  color: #e74c3c;
  margin-top: var(--spacing-xs);
}

/* Embedding 独立配置区 */
.embedding-section {
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.embedding-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-canvas);
}

.switch-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-ink);
  cursor: pointer;
  user-select: none;
}

.switch-label input {
  display: none;
}

.switch-track {
  width: 32px;
  height: 18px;
  background: var(--color-hairline);
  border-radius: 9px;
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}

.switch-track::after {
  content: '';
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--color-mute);
  top: 2px;
  left: 2px;
  transition: transform 0.2s, background 0.2s;
}

.switch-label input:checked + .switch-track {
  background: var(--color-primary);
}

.switch-label input:checked + .switch-track::after {
  transform: translateX(14px);
  background: var(--color-on-primary);
}

.switch-hint {
  font-size: 12px;
  color: var(--color-mute);
}

.embedding-fields {
  padding: var(--spacing-md) var(--spacing-lg) var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  border-top: 1px solid var(--color-hairline);
}

/* 操作按钮 */
.config-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-hairline);
}

.config-actions-right {
  display: flex;
  gap: var(--spacing-sm);
}

.cfg-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--color-hairline);
  background: var(--color-canvas);
  color: var(--color-ink);
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.cfg-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.cfg-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cfg-btn.primary {
  background: var(--color-primary);
  color: var(--color-on-primary);
  border-color: var(--color-primary);
}

.cfg-btn.primary:hover {
  background: var(--color-primary-soft);
}

/* 响应式 */
@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
  }
  .config-actions {
    flex-direction: column;
    gap: var(--spacing-sm);
  }
  .config-actions-right {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
