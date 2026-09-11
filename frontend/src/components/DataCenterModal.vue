<template>
  <div class="dc-overlay" :class="{ active: modelValue }" @click.self="close">
    <div class="dc-page">
      <!-- 顶部栏 -->
      <div class="dc-header">
        <div class="dc-title">
          <i class="fas fa-database"></i>
          <h3>数据中心</h3>
          <span class="dc-subtitle">岗位 JD 采集与管理</span>
        </div>
        <button class="dc-close" @click="close">&times;</button>
      </div>

      <div class="dc-body">
        <!-- 左侧模块导航：由后端 /modules 元数据驱动 -->
        <div class="dc-nav">
          <div
            v-for="m in modules"
            :key="m.key"
            class="dc-nav-item"
            :class="{ active: activeKey === m.key }"
            @click="activeKey = m.key"
          >
            <i :class="moduleIcon(m.key)"></i>
            <div class="dc-nav-info">
              <div class="dc-nav-name">{{ m.name }}</div>
              <div class="dc-nav-desc">{{ m.description }}</div>
            </div>
          </div>
          <div v-if="!modules.length && !loadingModules" class="dc-nav-empty">暂无可用采集模块</div>
        </div>

        <!-- 右侧模块内容：前端注册表映射组件，新模块只需在 registry.js 加映射 -->
        <div class="dc-content">
          <div v-if="loadingModules" class="dc-loading">
            <i class="fas fa-spinner fa-spin"></i> 模块加载中...
          </div>
          <component
            :is="activeComponent"
            v-else-if="activeComponent"
            :key="activeKey"
            :module="activeModule"
            :user-id="userId"
          />
          <div v-else class="dc-loading">该模块前端组件尚未注册</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import * as api from '@/api/index.js'
import { collectorComponents } from './data-center/registry.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  userId: { type: [Number, String], required: true }
})
const emit = defineEmits(['update:modelValue'])

const modules = ref([])
const activeKey = ref('')
const loadingModules = ref(false)

const activeModule = computed(() => modules.value.find(m => m.key === activeKey.value))
const activeComponent = computed(() => collectorComponents[activeKey.value])

function close() {
  emit('update:modelValue', false)
}

// 不同采集模块的导航图标（纯展示，新模块可在此补充）
function moduleIcon(key) {
  return {
    zhaopin: 'fas fa-briefcase'
  }[key] || 'fas fa-plug'
}

async function loadModules() {
  loadingModules.value = true
  try {
    const res = await api.getCollectorModules()
    modules.value = res.modules || []
    if (modules.value.length && !modules.value.find(m => m.key === activeKey.value)) {
      activeKey.value = modules.value[0].key
    }
  } catch {
    modules.value = []
  } finally {
    loadingModules.value = false
  }
}

watch(() => props.modelValue, (val) => {
  if (val) loadModules()
})
</script>

<style scoped>
.dc-overlay {
  position: fixed; inset: 0; z-index: 1500;
  background: rgba(0, 0, 0, 0.6);
  display: none;
}
.dc-overlay.active { display: block; }

.dc-page {
  position: absolute; inset: 24px;
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: 12px;
  display: flex; flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,.6);
}

.dc-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 22px;
  background: var(--color-canvas-soft);
  border-bottom: 1px solid var(--color-hairline);
}
.dc-title { display: flex; align-items: center; gap: 10px; }
.dc-title i { color: var(--color-primary); font-size: 18px; }
.dc-title h3 { margin: 0; font-size: 16px; color: var(--color-ink-strong); }
.dc-subtitle { font-size: 12.5px; color: var(--color-mute); }
.dc-close {
  border: none; background: none; font-size: 26px; line-height: 1;
  color: var(--color-mute); cursor: pointer; padding: 0 6px;
}
.dc-close:hover { color: var(--color-ink); }

.dc-body { flex: 1; display: flex; min-height: 0; }

.dc-nav {
  width: 240px; flex-shrink: 0;
  background: var(--color-canvas-soft);
  border-right: 1px solid var(--color-hairline);
  padding: 14px 10px; overflow-y: auto;
}
.dc-nav-item {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 12px 12px; border-radius: var(--radius-md); cursor: pointer; margin-bottom: 6px;
  border: 1px solid transparent;
}
.dc-nav-item:hover { background: var(--color-canvas); }
.dc-nav-item.active {
  background: rgba(0, 217, 146, 0.08);
  border-color: rgba(0, 217, 146, 0.35);
}
.dc-nav-item > i { color: var(--color-primary); margin-top: 3px; }
.dc-nav-name { font-size: 13.5px; font-weight: 600; color: var(--color-ink); }
.dc-nav-desc { font-size: 11.5px; color: var(--color-mute); margin-top: 2px; line-height: 1.4; }
.dc-nav-empty { text-align: center; color: var(--color-mute); font-size: 12.5px; padding: 20px 8px; }

.dc-content { flex: 1; overflow-y: auto; padding: 20px 24px; min-width: 0; }
.dc-loading { text-align: center; padding: 60px 0; color: var(--color-mute); font-size: 13.5px; }
</style>
