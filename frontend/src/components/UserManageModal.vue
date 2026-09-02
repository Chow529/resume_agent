<template>
  <div class="modal-overlay" :class="{ active: modelValue }" @click.self="close">
    <div class="modal">
      <div class="modal-header">
        <h3>账号管理</h3>
        <button class="modal-close" @click="close">&times;</button>
      </div>
      <div class="modal-body">
        <!-- 只读信息 -->
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input class="form-input" :value="authStore.username" disabled />
        </div>
        <div class="form-group">
          <label class="form-label">当前邮箱</label>
          <input class="form-input" :value="authStore.email" disabled />
        </div>

        <!-- 修改邮箱 -->
        <h4 style="color:#f2f2f2;margin:20px 0 12px;">修改邮箱</h4>
        <div class="form-group">
          <label class="form-label">新邮箱</label>
          <input class="form-input" v-model="newEmail" placeholder="请输入新邮箱" />
        </div>
        <div v-if="emailError" class="error-message show">{{ emailError }}</div>
        <div class="form-actions">
          <button class="btn btn-primary" @click="handleUpdateEmail">保存邮箱</button>
        </div>

        <!-- 修改密码 -->
        <h4 style="color:#f2f2f2;margin:20px 0 12px;">修改密码</h4>
        <div class="form-group">
          <label class="form-label">旧密码</label>
          <input class="form-input" type="password" v-model="oldPassword" />
        </div>
        <div class="form-group">
          <label class="form-label">新密码</label>
          <input class="form-input" type="password" v-model="newPassword" placeholder="至少8位" />
        </div>
        <div v-if="pwdError" class="error-message show">{{ pwdError }}</div>
        <div class="form-actions">
          <button class="btn btn-primary" @click="handleUpdatePassword">修改密码</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const authStore = useAuthStore()

const newEmail = ref('')
const emailError = ref('')
const oldPassword = ref('')
const newPassword = ref('')
const pwdError = ref('')

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function close() {
  emit('update:modelValue', false)
  resetForms()
}

function resetForms() {
  newEmail.value = ''
  emailError.value = ''
  oldPassword.value = ''
  newPassword.value = ''
  pwdError.value = ''
}

async function handleUpdateEmail() {
  emailError.value = ''
  if (!newEmail.value) {
    emailError.value = '请输入新邮箱'
    return
  }
  if (!EMAIL_RE.test(newEmail.value)) {
    emailError.value = '邮箱格式不正确'
    return
  }
  try {
    await authStore.updateEmail(newEmail.value)
    alert('邮箱修改成功！')
    await authStore.loadUserInfo()
    newEmail.value = ''
  } catch (e) {
    emailError.value = e.message || '修改邮箱失败'
  }
}

async function handleUpdatePassword() {
  pwdError.value = ''
  if (!oldPassword.value || !newPassword.value) {
    pwdError.value = '请填写旧密码和新密码'
    return
  }
  if (newPassword.value.length < 8) {
    pwdError.value = '新密码至少8位'
    return
  }
  try {
    await authStore.updatePassword(oldPassword.value, newPassword.value)
    alert('密码修改成功！请重新登录。')
    location.reload()
  } catch (e) {
    pwdError.value = e.message || '修改密码失败'
  }
}
</script>
