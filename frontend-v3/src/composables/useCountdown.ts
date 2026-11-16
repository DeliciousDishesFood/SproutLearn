// 服务端倒计时：以 server_now 校正本地时钟偏移，不信任浏览器时间。
import { computed, onBeforeUnmount, ref, watch, type Ref } from 'vue'

export function useCountdown(
  serverNow: Ref<string | null | undefined>,
  remainingSeconds: Ref<number | null | undefined>,
) {
  const secondsLeft = ref<number | null>(null)
  let targetAt = 0
  let timer: number | null = null

  function stop(): void {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  function tick(): void {
    if (secondsLeft.value === null) return
    const diff = Math.max(0, Math.ceil((targetAt - Date.now()) / 1000))
    secondsLeft.value = diff
    if (diff === 0) stop()
  }

  function sync(): void {
    stop()
    const remaining = remainingSeconds.value
    if (remaining === null || remaining === undefined) {
      secondsLeft.value = null
      return
    }
    const server = serverNow.value ? new Date(serverNow.value).getTime() : Date.now()
    const offset = Number.isNaN(server) ? 0 : server - Date.now()
    targetAt = Date.now() + offset + Math.max(0, remaining) * 1000
    secondsLeft.value = Math.max(0, Math.floor(remaining))
    if (secondsLeft.value > 0) {
      timer = window.setInterval(tick, 1000)
    }
  }

  watch([serverNow, remainingSeconds], sync, { immediate: true })
  onBeforeUnmount(stop)

  const label = computed(() => {
    if (secondsLeft.value === null) return '不限时'
    if (secondsLeft.value <= 0) return '已截止'
    const total = secondsLeft.value
    const hours = Math.floor(total / 3600)
    const minutes = Math.floor((total % 3600) / 60)
    const seconds = total % 60
    const pad = (n: number): string => String(n).padStart(2, '0')
    return hours > 0 ? `${pad(hours)}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`
  })

  const expired = computed(() => secondsLeft.value !== null && secondsLeft.value <= 0)
  const warning = computed(() => secondsLeft.value !== null && secondsLeft.value > 0 && secondsLeft.value <= 60)

  return { secondsLeft, label, expired, warning }
}
