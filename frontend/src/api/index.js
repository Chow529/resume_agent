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

/**
 * 流式对话：返回 { response, reader, abortController }，由调用方迭代 SSE 事件。
 * @param onChunk    收到 chunk 事件时回调 (content) => void
 * @param onDone     收到 done 事件时回调 (data) => void
 * @param onCancelled 收到 cancelled 事件时回调 (data) => void
 * @param onError    收到 error 事件时回调 (data) => void
 * @param onConfigRequired 收到 config_required 事件时回调 (data) => void
 * @returns { abortController, promise } 调用 abortController.abort() 可本地中止
 */
export function streamChat(sessionId, message, userId, { onChunk, onDone, onCancelled, onError, onConfigRequired } = {}) {
  const abortController = new AbortController()

  const promise = (async () => {
    const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
      body: JSON.stringify({ message, user_id: userId }),
      signal: abortController.signal
    })

    if (!res.ok) {
      let msg = `HTTP ${res.status}`
      try { const d = await res.json(); msg = d.detail || d.message || msg } catch {}
      throw new Error(msg)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buf = ''

    // 简易 SSE 解析：按双换行分割事件块
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })

      let idx
      // 一个 SSE 事件以 \n\n 结束
      while ((idx = buf.indexOf('\n\n')) !== -1) {
        const raw = buf.slice(0, idx)
        buf = buf.slice(idx + 2)

        let event = 'message'
        let data = ''
        for (const line of raw.split('\n')) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          else if (line.startsWith('data:')) data += line.slice(5).trim()
        }
        if (!data) continue

        let payload = {}
        try { payload = JSON.parse(data) } catch { payload = { content: data } }

        if (event === 'chunk' && onChunk) onChunk(payload.content || '')
        else if (event === 'done' && onDone) onDone(payload)
        else if (event === 'cancelled' && onCancelled) onCancelled(payload)
        else if (event === 'error' && onError) onError(payload)
        else if (event === 'config_required' && onConfigRequired) onConfigRequired(payload)
      }
    }
  })().catch(err => {
    // 本地 abort 不当作错误处理
    if (err.name === 'AbortError') return
    if (onError) onError({ message: err.message })
    else throw err
  })

  return { abortController, promise }
}

export function cancelChat(sessionId) {
  return fetch(`/api/sessions/${encodeURIComponent(sessionId)}/cancel`, {
    method: 'POST'
  }).then(handleResponse).catch(() => {})
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

// ========== Model Config APIs ==========

export function checkConfigStatus() {
  return fetch('/api/config/status').then(handleResponse)
}

export function loadModelConfig() {
  return fetch('/api/config/load').then(handleResponse)
}

export function testModelConfig(config) {
  return fetch('/api/config/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  }).then(handleResponse)
}

export function saveModelConfig(config) {
  return fetch('/api/config/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  }).then(handleResponse)
}

export function resetModelConfig() {
  return fetch('/api/config/reset', {
    method: 'POST'
  }).then(handleResponse)
}
