// 全局事件总线：跨组件事件通信（无依赖）
const listeners = {}

export function on(event, fn) {
  ;(listeners[event] ||= []).push(fn)
}

export function off(event, fn) {
  listeners[event] = (listeners[event] || []).filter(f => f !== fn)
}

export function emit(event, ...args) {
  ;(listeners[event] || []).forEach(fn => fn(...args))
}
