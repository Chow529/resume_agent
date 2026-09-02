<template>
  <div class="auth-modal" :class="{ active: modelValue }">
    <div class="auth-card">
      <!-- 登录表单 -->
      <template v-if="!isRegister">
        <h2 style="text-align:center;margin-bottom:24px;color:#f2f2f2;">登录</h2>
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input class="form-input" v-model="username" @keyup.enter="handleLogin" placeholder="请输入用户名" />
        </div>
        <div class="form-group">
          <label class="form-label">密码</label>
          <input class="form-input" type="password" v-model="password" @keyup.enter="handleLogin" placeholder="请输入密码" />
        </div>
        <div v-if="errorMsg" class="error-message show">{{ errorMsg }}</div>
        <div class="form-actions">
          <button class="btn btn-primary" @click="handleLogin">登录</button>
        </div>
        <div class="auth-toggle">
          没有账号？<a href="#" @click.prevent="switchToRegister">立即注册</a>
        </div>
      </template>

      <!-- 注册表单 -->
      <template v-else>
        <h2 style="text-align:center;margin-bottom:24px;color:#f2f2f2;">注册</h2>
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input class="form-input" v-model="regUsername" placeholder="请输入用户名（5-50字符）" />
        </div>
        <div class="form-group">
          <label class="form-label">邮箱</label>
          <input class="form-input" type="email" v-model="regEmail" placeholder="请输入邮箱地址" />
        </div>
        <div class="form-group">
          <label class="form-label">密码</label>
          <input class="form-input" type="password" v-model="regPassword" placeholder="请输入密码（至少8位）" />
        </div>
        <div v-if="errorMsg" class="error-message show">{{ errorMsg }}</div>
        <div v-if="successMsg" class="success-message show">{{ successMsg }}</div>
        <div class="form-actions">
          <button class="btn btn-primary" @click="handleRegister" :disabled="!!successMsg">注册</button>
          <button class="btn btn-outline" @click="isRegister = false">返回登录</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const authStore = useAuthStore()

const isRegister = ref(false)
const username = ref('')
const password = ref('')
const regUsername = ref('')
const regEmail = ref('')
const regPassword = ref('')
const errorMsg = ref('')
const successMsg = ref('')

// 认证后自动关闭（登录立即关闭，注册由 handleRegister 自行控制以显示成功消息）
watch(() => authStore.isAuthenticated, (val) => {
  if (val && !isRegister.value) {
    close()
  }
})

function close() {
  emit('update:modelValue', false)
  reset()
}

function reset() {
  username.value = ''
  password.value = ''
  regUsername.value = ''
  regEmail.value = ''
  regPassword.value = ''
  errorMsg.value = ''
  successMsg.value = ''
}

function switchToRegister() {
  errorMsg.value = ''
  isRegister.value = true
}

async function handleLogin() {
  errorMsg.value = ''
  if (!username.value || !password.value) {
    errorMsg.value = '用户名和密码不能为空'
    return
  }
  try {
    const res = await authStore.login(username.value, password.value)
    if (!res.success) {
      errorMsg.value = res.message || '登录失败，请检查用户名和密码'
      return
    }
    await authStore.loadUserInfo()
    // close 由 App.vue 中 isAuthenticated watcher 自动触发
  } catch (e) {
    errorMsg.value = e.message || '登录失败，请检查用户名和密码'
  }
}

async function handleRegister() {
  errorMsg.value = ''
  if (!regUsername.value || !regEmail.value || !regPassword.value) {
    errorMsg.value = '所有字段均为必填'
    return
  }
  if (regPassword.value.length < 8) {
    errorMsg.value = '密码至少8位'
    return
  }

  try {
    const usernameRes = await authStore.checkAvailable('username', regUsername.value)
    if (!usernameRes.available) {
      errorMsg.value = usernameRes.message
      return
    }
  } catch (e) {
    errorMsg.value = e.message || '检查用户名失败'
    return
  }

  try {
    const emailRes = await authStore.checkAvailable('email', regEmail.value)
    if (!emailRes.available) {
      errorMsg.value = emailRes.message
      return
    }
  } catch (e) {
    errorMsg.value = e.message || '检查邮箱失败'
    return
  }

  try {
    await authStore.register(regUsername.value, regEmail.value, regPassword.value)
    successMsg.value = '注册成功！您已自动登录，欢迎加入！'
    await authStore.loadUserInfo()
    // 注册模式：先显示成功消息，2秒后关闭
    setTimeout(() => {
      close()
    }, 2000)
  } catch (e) {
    errorMsg.value = e.message || '注册失败'
  }
}
</script>
