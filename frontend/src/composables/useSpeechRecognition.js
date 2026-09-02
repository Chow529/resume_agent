import { ref, onBeforeUnmount } from 'vue'

export function useSpeechRecognition() {
  const isSupported = ref(
    typeof window !== 'undefined' &&
    (!!window.SpeechRecognition || !!window.webkitSpeechRecognition)
  )
  const isRecording = ref(false)
  const finalTranscript = ref('')
  const interimTranscript = ref('')
  const timerDisplay = ref('00:00')
  const statusText = ref('')
  const statusType = ref('') // '' | 'info' | 'error' | 'warning'

  let recognition = null
  let lastFinalText = ''
  let timerInterval = null
  let startTime = 0
  let maxTimer = null
  let isUnexpectedStop = false

  if (isSupported.value) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    recognition = new SpeechRecognition()
    recognition.lang = 'zh-CN'
    recognition.continuous = false
    recognition.interimResults = true

    recognition.onresult = (event) => {
      let interim = ''
      let final = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          final += transcript
        } else {
          interim += transcript
        }
      }
      if (final) {
        finalTranscript.value += final
        lastFinalText = final
      }
      interimTranscript.value = interim
    }

    recognition.onend = () => {
      isRecording.value = false
      interimTranscript.value = ''
      stopTimer()

      if (lastFinalText) {
        applyFinalTextToInput()
      } else if (isUnexpectedStop) {
        setStatus('语音识别意外停止，请重试', 'warning')
      }
      isUnexpectedStop = false
    }

    recognition.onerror = (event) => {
      isRecording.value = false
      interimTranscript.value = ''
      stopTimer()

      const errorMessages = {
        'not-allowed': '麦克风权限被拒绝，请在浏览器设置中允许麦克风访问',
        'no-speech': '未检测到语音输入，请重试',
        'audio-capture': '未找到麦克风设备',
        'network': '网络错误，语音识别失败',
        'aborted': '语音识别已取消',
        'language-not-supported': '当前语言不支持语音识别'
      }
      const msg = errorMessages[event.error] || `语音识别错误: ${event.error}`
      setStatus(msg, 'error')
      isUnexpectedStop = false
    }
  }

  function applyFinalTextToInput() {
    // 将识别结果填入 — 由组件消费 finalTranscript
    // 组件可通过 watch finalTranscript 来更新 input
    lastFinalText = ''
  }

  function setStatus(text, type = 'info') {
    statusText.value = text
    statusType.value = type
  }

  function startTimer() {
    startTime = Date.now()
    timerInterval = setInterval(() => {
      const elapsed = Date.now() - startTime
      const seconds = Math.floor(elapsed / 1000)
      const mins = String(Math.floor(seconds / 60)).padStart(2, '0')
      const secs = String(seconds % 60).padStart(2, '0')
      timerDisplay.value = `${mins}:${secs}`
    }, 100)

    // 最大录音 60 秒
    maxTimer = setTimeout(() => {
      if (isRecording.value) {
        stopRecording()
        setStatus('已达最大录音时长（60秒）', 'warning')
      }
    }, 60000)
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval)
      timerInterval = null
    }
    if (maxTimer) {
      clearTimeout(maxTimer)
      maxTimer = null
    }
  }

  function startRecording() {
    if (!isSupported.value || !recognition) {
      setStatus('当前浏览器不支持语音识别', 'error')
      return
    }

    finalTranscript.value = ''
    interimTranscript.value = ''
    lastFinalText = ''
    isUnexpectedStop = true
    isRecording.value = true
    setStatus('正在录音...', 'info')
    startTimer()

    try {
      recognition.start()
    } catch (e) {
      // 可能已经在运行
      isRecording.value = false
      stopTimer()
      setStatus('无法启动语音识别', 'error')
    }
  }

  function stopRecording() {
    if (recognition && isRecording.value) {
      isUnexpectedStop = false
      isRecording.value = false
      recognition.stop()
      stopTimer()
      setStatus('录音结束', 'info')
    }
  }

  function cancelRecording() {
    if (recognition && isRecording.value) {
      isUnexpectedStop = false
      lastFinalText = ''
      isRecording.value = false
      recognition.abort()
      stopTimer()
      setStatus('已取消录音', 'warning')
    }
  }

  function resetUI() {
    finalTranscript.value = ''
    interimTranscript.value = ''
    timerDisplay.value = '00:00'
    statusText.value = ''
    statusType.value = ''
    isRecording.value = false
    lastFinalText = ''
    stopTimer()
  }

  onBeforeUnmount(() => {
    stopTimer()
    if (recognition && isRecording.value) {
      try { recognition.abort() } catch {}
    }
  })

  return {
    isSupported,
    isRecording,
    finalTranscript,
    interimTranscript,
    timerDisplay,
    statusText,
    statusType,
    startRecording,
    stopRecording,
    cancelRecording,
    resetUI
  }
}
