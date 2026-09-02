// API 层 - 封装所有后端请求

// 统一响应处理：检查 HTTP 状态码，非 2xx 时抛出异常
async function handleResponse(r) {
  const data = await r.json()
  if (!r.ok) {
    const msg = data.detail || data.message || `HTTP ${r.status}`
    throw new Error(msg)
  }
  return data
}

// ========== Auth APIs ==========

export function login(username, password) {
  return fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  }).then(handleResponse)
}

export function register(username, email, password) {
  return fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password })
  }).then(handleResponse)
}

export function checkAvailable(field, value) {
  return fetch(`/api/auth/check?field=${encodeURIComponent(field)}&value=${encodeURIComponent(value)}`)
    .then(handleResponse)
}

export function getUserInfo(userId) {
  return fetch(`/api/auth/me?user_id=${encodeURIComponent(userId)}`)
    .then(handleResponse)
}

export function logoutApi(userId) {
  return fetch('/api/auth/logout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId })
  }).then(handleResponse)
}

export function updateEmail(userId, email) {
  return fetch('/api/auth/user/email', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, email })
  }).then(handleResponse)
}

export function updatePassword(userId, oldPassword, newPassword) {
  return fetch('/api/auth/user/password', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, old_password: oldPassword, new_password: newPassword })
  }).then(handleResponse)
}

// ========== Session APIs ==========

export function initSession(sessionId, userId) {
  const params = userId ? `?user_id=${encodeURIComponent(userId)}` : ''
  return fetch(`/api/sessions/${encodeURIComponent(sessionId)}/init${params}`).then(handleResponse)
}

export function bindUserToSession(sessionId, userId) {
  return fetch(`/api/sessions/${encodeURIComponent(sessionId)}/user`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId })
  }).then(handleResponse)
}

export function getSessionStatus(sessionId) {
  return fetch(`/api/sessions/${encodeURIComponent(sessionId)}/status`).then(handleResponse)
}

export function sendMessage(sessionId, message, userId) {
  return fetch(`/api/sessions/${encodeURIComponent(sessionId)}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, user_id: userId })
  }).then(handleResponse)
}

export function getLatestSession(userId) {
  return fetch(`/api/sessions/latest?user_id=${encodeURIComponent(userId)}`).then(handleResponse)
}

export function getSessionList(userId) {
  return fetch(`/api/sessions/list?user_id=${encodeURIComponent(userId)}`).then(handleResponse)
}

export function getSessionMessages(dbSessionId) {
  return fetch(`/api/sessions/${encodeURIComponent(dbSessionId)}/messages`).then(handleResponse)
}

export function renameSession(dbSessionId, name) {
  return fetch(`/api/sessions/${encodeURIComponent(dbSessionId)}/rename`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  }).then(handleResponse)
}

export function deleteSession(dbSessionId) {
  return fetch(`/api/sessions/${encodeURIComponent(dbSessionId)}/delete`, {
    method: 'DELETE'
  }).then(handleResponse)
}

// ========== Resume APIs ==========

export function uploadResume(file, userId, sessionId) {
  const formData = new FormData()
  formData.append('file', file)
  return fetch(`/api/resume/upload?user_id=${encodeURIComponent(userId)}&session_id=${encodeURIComponent(sessionId)}`, {
    method: 'PUT',
    body: formData
  }).then(handleResponse)
}

export function getResumeList(userId) {
  return fetch(`/api/resume/list?user_id=${encodeURIComponent(userId)}`).then(handleResponse)
}

export function activateResume(resumeId, sessionId) {
  return fetch(`/api/resume/${encodeURIComponent(resumeId)}/activate?session_id=${encodeURIComponent(sessionId)}`, {
    method: 'PUT'
  }).then(handleResponse)
}

export function deleteResume(resumeId) {
  return fetch(`/api/resume/${encodeURIComponent(resumeId)}`, {
    method: 'DELETE'
  }).then(handleResponse)
}

// ========== Knowledge Base APIs ==========

export function getKbDocuments() {
  return fetch('/api/vector/manual/list').then(handleResponse)
}

export function addKbDocument(question, answer, section) {
  return fetch('/api/vector/manual/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, answer, section })
  }).then(handleResponse)
}

export function deleteKbDocument(docId) {
  return fetch(`/api/vector/manual/${encodeURIComponent(docId)}`, {
    method: 'DELETE'
  }).then(handleResponse)
}
