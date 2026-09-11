<template>
  <div class="zc-module">
    <!-- 爬取表单 -->
    <div class="zc-form-card">
      <h4><i class="fas fa-cloud-download-alt"></i> 岗位采集</h4>
      <p class="zc-desc">{{ module.description }}</p>

      <div class="zc-form">
        <template v-for="p in module.params" :key="p.name">
          <label class="zc-field">
            <span class="zc-label">{{ p.label }}<em v-if="p.required">*</em></span>

            <select v-if="p.type === 'select'" v-model="form[p.name]">
              <option value="" disabled>请选择</option>
              <option v-for="opt in p.options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>

            <textarea
              v-else-if="p.type === 'textarea'"
              v-model="form[p.name]"
              rows="2"
              :placeholder="p.placeholder"
            ></textarea>

            <input
              v-else
              v-model="form[p.name]"
              :type="p.type === 'number' ? 'number' : 'text'"
              :placeholder="p.placeholder"
            />
          </label>
        </template>

        <div class="zc-form-actions">
          <button class="btn btn-primary" :disabled="scraping" @click="startScrape">
            <i :class="scraping ? 'fas fa-spinner fa-spin' : 'fas fa-play'"></i>
            {{ scraping ? '采集中...' : '开始爬取' }}
          </button>
          <button v-if="scraping" class="btn btn-outline" @click="stopScrape">停止</button>
        </div>
      </div>

      <!-- 进度 -->
      <div v-if="scraping || progress" class="zc-progress">
        <i v-if="scraping" class="fas fa-spinner fa-spin"></i>
        <span v-if="progress">
          正在爬取「{{ progress.keyword }}」第 {{ progress.page }}/{{ progress.total_pages || '?' }} 页，
          已采集 {{ progress.collected }} 条
        </span>
        <span v-else>任务启动中...</span>
      </div>
      <div v-if="scrapeMsg" class="zc-scrape-msg" :class="scrapeMsgType">{{ scrapeMsg }}</div>
    </div>

    <!-- 数据区：个人数据 / 公用数据 / 个人排名 / 公用排名 -->
    <div class="zc-result-card">
      <div class="zc-tabs">
        <span class="zc-tab" :class="{ active: scope === 'personal' }" @click="switchScope('personal')">
          个人数据 <em>{{ personalCount }}</em>
        </span>
        <span class="zc-tab" :class="{ active: scope === 'public' }" @click="switchScope('public')">
          公用数据 <em>{{ publicCount }}</em>
        </span>
        <span class="zc-tab" :class="{ active: scope === 'personal_rank' }" @click="switchScope('personal_rank')">
          个人排名
        </span>
        <span class="zc-tab" :class="{ active: scope === 'public_rank' }" @click="switchScope('public_rank')">
          公用排名
        </span>
        <div v-if="!isRank" class="zc-tab-tools">
          <input v-model="keyword" placeholder="搜索岗位/公司/关键词" @keyup.enter="loadList" />
          <button class="btn btn-outline zc-btn-sm" @click="loadList" title="搜索">
            <i class="fas fa-search"></i>
          </button>
          <button class="btn btn-outline zc-btn-sm" @click="loadList" title="刷新">
            <i class="fas fa-sync-alt"></i>
          </button>
        </div>
        <div v-else class="zc-tab-tools">
          <button class="btn btn-outline zc-btn-sm" @click="loadList" title="刷新">
            <i class="fas fa-sync-alt"></i>
          </button>
        </div>
      </div>

      <div v-if="loading" class="zc-loading"><i class="fas fa-spinner fa-spin"></i> 加载中...</div>

      <!-- 排名视图 -->
      <div v-else-if="isRank" class="zc-table-wrap">
        <table v-if="items.length" class="zc-table">
          <thead>
            <tr>
              <th style="width: 64px;">排名</th>
              <th>岗位名称</th>
              <th>公司</th>
              <th>城市</th>
              <th>薪资</th>
              <th>使用次数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in items" :key="`${item.id}-${idx}`">
              <td><span class="zc-rank" :class="{ top: idx < 3 }">{{ idx + 1 }}</span></td>
              <td class="zc-jobname" :title="item.job_name">{{ item.job_name || '-' }}</td>
              <td>{{ item.company_name || '-' }}</td>
              <td>{{ item.city || '-' }}</td>
              <td class="zc-salary">{{ item.salary || '-' }}</td>
              <td><span class="zc-use-count">{{ item.use_count || 0 }} 次</span></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="zc-empty">
          <i class="fas fa-trophy"></i>
          <p>{{ scope === 'personal_rank' ? '暂无个人排名，开始面试并选择岗位后生成' : '暂无公用排名，公开岗位被使用后生成' }}</p>
        </div>
      </div>

      <!-- 数据列表视图 -->
      <div v-else class="zc-table-wrap">
        <table v-if="items.length" class="zc-table">
          <thead>
            <tr>
              <th>岗位名称</th>
              <th>公司</th>
              <th>城市</th>
              <th>薪资</th>
              <th>学历</th>
              <th>经验</th>
              <th>关键词</th>
              <th>来源</th>
              <th style="width: 160px;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="zc-jobname" :title="item.job_name">{{ item.job_name || '-' }}</td>
              <td>{{ item.company_name || '-' }}</td>
              <td>{{ [item.city, item.district].filter(Boolean).join(' ') || '-' }}</td>
              <td class="zc-salary">{{ item.salary || '-' }}</td>
              <td>{{ item.education || '-' }}</td>
              <td>{{ item.experience || '-' }}</td>
              <td>{{ item.keyword || '-' }}</td>
              <td><span class="zc-source-tag">{{ sourceName(item.source) }}</span></td>
              <td class="zc-actions">
                <button class="zc-link" title="查看JD" @click="viewDetail(item)"><i class="fas fa-eye"></i></button>
                <!-- 个人数据列表仅展示未公开的私有数据；已公开数据请到公用数据查看 -->
                <template v-if="scope === 'personal'">
                  <button class="zc-link" title="设为公用" @click="togglePublic(item)">
                    <i class="fas fa-lock-open"></i>
                  </button>
                  <button class="zc-link danger" title="删除" @click="removeItem(item)">
                    <i class="fas fa-trash"></i>
                  </button>
                </template>
                <template v-else>
                  <span v-if="isMine(item)" class="zc-owner" title="我公开的数据">我的</span>
                  <span v-else class="zc-owner">公用</span>
                  <button v-if="isMine(item)" class="zc-link danger" title="删除" @click="removeItem(item)">
                    <i class="fas fa-trash"></i>
                  </button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="zc-empty">
          <i class="fas fa-inbox"></i>
          <p>{{ scope === 'personal' ? '暂无个人数据，填写上方表单开始爬取吧' : '暂无公用数据，可在个人数据中点击开锁图标公开' }}</p>
        </div>
      </div>
    </div>

    <!-- JD 详情弹层 -->
    <div v-if="detail" class="zc-detail-overlay" @click.self="detail = null">
      <div class="zc-detail-modal">
        <div class="zc-detail-header">
          <h4>{{ detail.job_name }}</h4>
          <button @click="detail = null">&times;</button>
        </div>
        <pre class="zc-detail-content">{{ detail.jd_content || '暂无JD内容' }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import * as api from '@/api/index.js'

const props = defineProps({
  module: { type: Object, required: true },
  userId: { type: [Number, String], required: true }
})

// 表单默认值由后端参数元数据驱动
const form = reactive({})
for (const p of props.module.params || []) {
  form[p.name] = p.default ?? ''
}

const scraping = ref(false)
const progress = ref(null)
const scrapeMsg = ref('')
const scrapeMsgType = ref('')
let abortController = null

// personal/public 数据列表；personal_rank/public_rank 排名视图
const scope = ref('personal')
const keyword = ref('')
const items = ref([])
const loading = ref(false)
const personalCount = ref(0)
const publicCount = ref(0)
const detail = ref(null)

const isRank = computed(() => scope.value.endsWith('_rank'))

function sourceName(source) {
  return { zhaopin: '智联招聘' }[source] || source
}

// 是否为本人公开的数据（个人数据公开后移入公用列表展示）
function isMine(item) {
  return String(item.user_id) === String(props.userId)
}

async function startScrape() {
  // 必填校验
  for (const p of props.module.params || []) {
    if (p.required && !String(form[p.name] ?? '').trim()) {
      scrapeMsg.value = `请填写：${p.label}`
      scrapeMsgType.value = 'error'
      return
    }
  }
  scraping.value = true
  progress.value = null
  scrapeMsg.value = ''

  const handle = api.scrapeStream(props.userId, props.module.key, { ...form }, {
    onProgress: (p) => { progress.value = p },
    onDone: (data) => {
      scraping.value = false
      const s = data.saved || {}
      scrapeMsg.value = `爬取完成：共 ${s.total ?? 0} 条，新增 ${s.inserted ?? 0} 条，更新已存在 ${s.updated ?? 0} 条`
      scrapeMsgType.value = 'success'
      loadList()
      loadCounts()
    },
    onError: (data) => {
      scraping.value = false
      scrapeMsg.value = `爬取失败：${data.message || '未知错误'}`
      scrapeMsgType.value = 'error'
    }
  })
  abortController = handle.abortController
}

function stopScrape() {
  if (abortController) {
    try { abortController.abort() } catch {}
    scraping.value = false
    scrapeMsg.value = '已停止爬取，已采集数据可能尚未入库'
    scrapeMsgType.value = 'error'
  }
}

async function loadList() {
  loading.value = true
  try {
    if (isRank.value) {
      const res = await api.listJdRanking(
        props.userId,
        scope.value === 'public_rank' ? 'public' : 'personal'
      )
      items.value = res.items || []
    } else {
      const res = await api.listJds(props.userId, scope.value, keyword.value.trim())
      items.value = res.items || []
    }
  } catch (e) {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function loadCounts() {
  try {
    const [personal, publicRes] = await Promise.all([
      api.listJds(props.userId, 'personal'),
      api.listJds(props.userId, 'public')
    ])
    personalCount.value = (personal.items || []).length
    publicCount.value = (publicRes.items || []).length
  } catch {}
}

function switchScope(s) {
  if (scope.value === s) return
  scope.value = s
  keyword.value = ''
  loadList()
}

// 设为公用（单向：公开后不可改回个人数据）
async function togglePublic(item) {
  const tip = `确定将「${item.job_name}」公开为公用数据吗？\n公开后所有用户都可以查看并用于面试，且不能再改回个人数据。`
  if (!confirm(tip)) return
  const res = await api.setJdVisibility(item.id, props.userId, 1)
  if (res.success) {
    item.is_public = 1
    loadCounts()
    // 公开后从个人数据列表移除，改在公用数据中展示
    loadList()
  } else {
    alert(res.message || '操作失败')
  }
}

async function removeItem(item) {
  if (!confirm(`确定删除「${item.job_name}」吗？`)) return
  const res = await api.deleteJd(item.id, props.userId)
  if (res.success) {
    loadList()
    loadCounts()
  } else {
    alert(res.message || '删除失败')
  }
}

function viewDetail(item) {
  detail.value = item
}

onMounted(() => {
  loadList()
  loadCounts()
})
</script>

<style scoped>
.zc-module { display: flex; flex-direction: column; gap: 16px; }

.zc-form-card, .zc-result-card {
  background: var(--color-canvas-soft);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  padding: 18px 20px;
}
.zc-form-card h4 { margin: 0 0 6px; font-size: 15px; color: var(--color-ink-strong); }
.zc-form-card h4 i { color: var(--color-primary); margin-right: 6px; }
.zc-desc { margin: 0 0 14px; font-size: 12.5px; color: var(--color-mute); }

.zc-form { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px; }
.zc-field { display: flex; flex-direction: column; gap: 6px; }
.zc-field:nth-child(2) { grid-column: 1 / -1; }
.zc-label { font-size: 13px; color: var(--color-body); }
.zc-label em { color: #ef4444; font-style: normal; margin-left: 2px; }
.zc-field input, .zc-field select, .zc-field textarea {
  width: 100%;
  padding: 8px 10px;
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-sm);
  color: var(--color-ink);
  font-size: 13px;
  font-family: inherit;
  box-sizing: border-box;
  outline: none;
}
.zc-field input::placeholder, .zc-field textarea::placeholder { color: var(--color-mute); }
.zc-field input:focus, .zc-field select:focus, .zc-field textarea:focus { border-color: var(--color-primary); }
.zc-field textarea { resize: vertical; }

.zc-form-actions { grid-column: 1 / -1; display: flex; gap: 10px; }

.zc-progress {
  margin-top: 12px; padding: 8px 12px;
  background: rgba(0, 217, 146, 0.08);
  border: 1px solid rgba(0, 217, 146, 0.25);
  color: var(--color-primary-soft);
  border-radius: var(--radius-sm); font-size: 13px;
  display: flex; align-items: center; gap: 8px;
}
.zc-scrape-msg { margin-top: 8px; font-size: 13px; }
.zc-scrape-msg.success { color: var(--color-primary); }
.zc-scrape-msg.error { color: #f87171; }

.zc-tabs { display: flex; align-items: center; gap: 4px; border-bottom: 1px solid var(--color-hairline); margin-bottom: 14px; flex-wrap: wrap; }
.zc-tab {
  padding: 8px 12px; font-size: 13px; color: var(--color-mute); cursor: pointer;
  border-bottom: 2px solid transparent;
}
.zc-tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); font-weight: 600; }
.zc-tab em {
  font-style: normal; font-size: 12px; color: var(--color-mute);
  background: var(--color-canvas); border: 1px solid var(--color-hairline);
  border-radius: 8px; padding: 1px 7px; margin-left: 4px;
}
.zc-tab-tools { margin-left: auto; display: flex; gap: 6px; padding-bottom: 6px; }
.zc-tab-tools input {
  padding: 6px 10px; background: var(--color-canvas);
  border: 1px solid var(--color-hairline); border-radius: var(--radius-sm);
  color: var(--color-ink); font-size: 12.5px; width: 200px; outline: none;
}
.zc-tab-tools input::placeholder { color: var(--color-mute); }
.zc-tab-tools input:focus { border-color: var(--color-primary); }
.zc-btn-sm { padding: 6px 10px; font-size: 12px; }

.zc-loading, .zc-empty { text-align: center; padding: 40px 0; color: var(--color-mute); font-size: 13px; }
.zc-empty i { font-size: 34px; display: block; margin-bottom: 10px; }

.zc-table-wrap { overflow-x: auto; max-height: 420px; overflow-y: auto; }
.zc-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.zc-table th, .zc-table td {
  padding: 9px 10px; text-align: left; border-bottom: 1px solid var(--color-hairline); white-space: nowrap;
  color: var(--color-body);
}
.zc-table th {
  position: sticky; top: 0; background: var(--color-canvas-soft);
  color: var(--color-mute); font-weight: 600; z-index: 1;
}
.zc-jobname { color: var(--color-primary-soft); font-weight: 500; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
.zc-salary { color: var(--color-primary); }
.zc-source-tag {
  background: rgba(0, 217, 146, 0.12); color: var(--color-primary-soft);
  padding: 2px 8px; border-radius: 10px; font-size: 11.5px;
}
.zc-rank {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 24px; height: 24px; padding: 0 6px;
  border-radius: 6px; font-weight: 700; font-size: 12px;
  background: var(--color-canvas); color: var(--color-mute);
  border: 1px solid var(--color-hairline);
}
.zc-rank.top { background: rgba(0, 217, 146, 0.15); color: var(--color-primary); border-color: rgba(0, 217, 146, 0.4); }
.zc-use-count { color: var(--color-ink); font-weight: 600; }
.zc-actions { display: flex; gap: 10px; align-items: center; }
.zc-link { border: none; background: none; cursor: pointer; color: var(--color-primary-soft); font-size: 13px; padding: 2px; }
.zc-link:hover { color: var(--color-primary); }
.zc-link.danger { color: #f87171; }
.zc-owner { font-size: 11.5px; color: var(--color-primary); }

.zc-detail-overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6);
  display: flex; align-items: center; justify-content: center; z-index: 2000;
}
.zc-detail-modal {
  background: var(--color-canvas-soft);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  width: 640px; max-width: 92vw;
  max-height: 80vh; display: flex; flex-direction: column; overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,.6);
}
.zc-detail-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 18px; border-bottom: 1px solid var(--color-hairline);
}
.zc-detail-header h4 { margin: 0; font-size: 15px; color: var(--color-ink-strong); }
.zc-detail-header button { border: none; background: none; font-size: 22px; cursor: pointer; color: var(--color-mute); }
.zc-detail-header button:hover { color: var(--color-ink); }
.zc-detail-content {
  margin: 0; padding: 16px 18px; overflow: auto;
  font-family: inherit; font-size: 13px; line-height: 1.7; white-space: pre-wrap;
  color: var(--color-body);
}
</style>
