<template>
  <div class="modal-overlay" :class="{ active: modelValue }" @click.self="close">
    <div class="modal jd-modal">
      <div class="modal-header">
        <h3>选择目标岗位</h3>
        <button class="modal-close" @click="close">&times;</button>
      </div>

      <div class="modal-body">
        <p class="jd-tip">
          <i class="fas fa-info-circle"></i>
          从你的个人数据或公用数据中选择目标岗位，面试将严格围绕该岗位 JD 与你的简历提问。
        </p>

        <div class="jd-filter">
          <input v-model="keyword" type="text" placeholder="搜索岗位 / 公司 / 关键词..." />
          <button class="btn btn-outline jd-btn-sm" @click="openDataCenter">
            <i class="fas fa-database"></i> 去采集岗位
          </button>
        </div>

        <div v-if="loading" class="jd-loading"><i class="fas fa-spinner fa-spin"></i> 加载中...</div>

        <div v-else class="jd-groups">
          <div v-for="group in groups" :key="group.key" class="jd-group">
            <div class="jd-group-title">
              {{ group.label }}
              <em>{{ group.items.length }}</em>
            </div>
            <div v-if="!group.items.length" class="jd-group-empty">
              {{ group.key === 'personal' ? '暂无个人数据，可先去数据中心爬取' : '暂无公用数据' }}
            </div>
            <label
              v-for="item in group.items"
              :key="item.id"
              class="jd-item"
              :class="{ active: selectedId === item.id }"
            >
              <input type="radio" name="jd-choice" :value="item.id" v-model="selectedId" />
              <div class="jd-item-info">
                <div class="jd-item-name">{{ item.job_name || '未命名岗位' }}</div>
                <div class="jd-item-meta">
                  <span>{{ item.company_name || '-' }}</span>
                  <span>{{ [item.city, item.district].filter(Boolean).join(' ') || '-' }}</span>
                  <span class="jd-salary">{{ item.salary || '薪资面议' }}</span>
                  <span class="jd-source">{{ sourceName(item.source) }}</span>
                </div>
              </div>
            </label>
          </div>

          <div v-if="!filtered.length" class="jd-empty">
            <i class="fas fa-inbox"></i>
            <p>没有匹配的岗位数据</p>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-outline jd-skip-btn" title="不选定岗位，由 AI 根据简历中的意向自动分析并查询岗位信息" @click="skip">
          <i class="fas fa-wand-magic-sparkles"></i> 跳过，由 AI 推荐
        </button>
        <div class="jd-footer-right">
          <button class="btn btn-outline" @click="close">取消</button>
          <button class="btn btn-primary" :disabled="!selected" @click="confirm">
            开始面试
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import * as api from '@/api/index.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  userId: { type: [Number, String], required: true }
})
const emit = defineEmits(['update:modelValue', 'select', 'skip', 'open-data-center'])

const all = ref([])
const loading = ref(false)
const selectedId = ref(null)
const keyword = ref('')

const selected = computed(() => all.value.find(i => i.id === selectedId.value))

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return all.value
  return all.value.filter(i =>
    [i.job_name, i.company_name, i.keyword].some(v => String(v || '').toLowerCase().includes(kw))
  )
})

const groups = computed(() => [
  { key: 'personal', label: '个人数据', items: filtered.value.filter(i => i.scope === 'personal') },
  { key: 'public', label: '公用数据', items: filtered.value.filter(i => i.scope === 'public') }
])

function sourceName(source) {
  return { zhaopin: '智联招聘' }[source] || source
}

function close() {
  emit('update:modelValue', false)
}

function confirm() {
  if (!selected.value) return
  emit('select', selected.value)
  close()
}

// 跳过选岗：不携带 jdId 发起面试，走旧流程（Agent 通过工具从简历提取意向并查询岗位信息）
function skip() {
  emit('skip')
  close()
}

function openDataCenter() {
  close()
  emit('open-data-center')
}

async function loadChoices() {
  loading.value = true
  selectedId.value = null
  keyword.value = ''
  try {
    const res = await api.getJdChoices(props.userId)
    all.value = res.items || []
  } catch {
    all.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.modelValue, (val) => {
  if (val) loadChoices()
})
</script>

<style scoped>
/* 容器复用全局 .modal 深色背景，这里只调宽高与布局 */
.jd-modal {
  width: 92vw;
  max-width: 720px;
  max-height: 84vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-body { overflow-y: auto; }
.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 14px 24px;
  border-top: 1px solid var(--color-hairline);
}
.jd-footer-right { display: flex; gap: 10px; }
.jd-skip-btn i { margin-right: 4px; }

.jd-tip {
  margin: 0 0 14px;
  font-size: 12.5px;
  color: var(--color-body);
  background: rgba(0, 217, 146, 0.08);
  border: 1px solid rgba(0, 217, 146, 0.25);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
}
.jd-tip i { color: var(--color-primary); margin-right: 6px; }

.jd-filter { display: flex; gap: 8px; margin-bottom: 14px; }
.jd-filter input {
  flex: 1;
  padding: 8px 12px;
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-sm);
  color: var(--color-ink);
  font-size: 13px;
  outline: none;
}
.jd-filter input::placeholder { color: var(--color-mute); }
.jd-filter input:focus { border-color: var(--color-primary); }
.jd-btn-sm { padding: 6px 12px; font-size: 12.5px; white-space: nowrap; }

.jd-loading, .jd-empty { text-align: center; padding: 30px 0; color: var(--color-mute); font-size: 13px; }
.jd-empty i { font-size: 30px; display: block; margin-bottom: 8px; }

.jd-group { margin-bottom: 16px; }
.jd-group-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-ink);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.jd-group-title em {
  font-style: normal;
  font-size: 11.5px;
  color: var(--color-mute);
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  padding: 1px 7px;
}
.jd-group-empty { font-size: 12.5px; color: var(--color-mute); padding: 6px 0 10px; }

.jd-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  background: var(--color-canvas);
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.jd-item:hover { border-color: var(--color-primary-soft); }
.jd-item.active {
  border-color: var(--color-primary);
  background: rgba(0, 217, 146, 0.08);
}
.jd-item input[type="radio"] { accent-color: var(--color-primary); flex-shrink: 0; }
.jd-item-info { flex: 1; min-width: 0; }
.jd-item-name { font-size: 13.5px; font-weight: 600; color: var(--color-ink-strong); margin-bottom: 4px; }
.jd-item-meta { display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: var(--color-body); }
.jd-salary { color: var(--color-primary); }
.jd-source {
  background: rgba(0, 217, 146, 0.12);
  color: var(--color-primary-soft);
  padding: 0 7px;
  border-radius: 8px;
  font-size: 11px;
}
</style>
