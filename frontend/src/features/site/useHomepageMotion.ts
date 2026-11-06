import { computed, onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import { theme } from '../../styles/theme'

/** The route owns and releases its canvas, observers, listeners and animation frames. */
export function useHomepageMotion(root: Ref<HTMLElement | undefined>) {
  const paused = ref(false), reduced = ref(false), backgrounded = ref(false)
  const stopped = computed(() => paused.value || reduced.value)
  const product = ref(0), stage = ref(0)
  const cleanup: (() => void)[] = []
  let mobile = false, visible = true, focused = false, hovering = false, manualStage = false, mounted = false
  let frame = 0, scrollFrame = 0, lastFrame = 0, elapsed = 0, lightTime = 0, width = 0, height = 0
  let canvas: HTMLCanvasElement | null = null, context: CanvasRenderingContext2D | null = null

  function slot(index: number) { return (index - product.value + 3) % 3 }
  function selectProduct(index: number) { product.value = (index + 3) % 3; elapsed = 0 }
  function selectStage(index: number) { manualStage = true; stage.value = index }
  function galleryKey(event: KeyboardEvent) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    selectProduct(event.key === 'Home' ? 0 : event.key === 'End' ? 2 : product.value + (event.key === 'ArrowRight' ? 1 : -1))
  }
  function tilt(event: PointerEvent) {
    if (event.pointerType !== 'mouse' || stopped.value || mobile) return
    const element = event.currentTarget as HTMLElement, box = element.getBoundingClientRect()
    element.style.setProperty('--rx', `${-(event.clientY - box.top - box.height / 2) / box.height * 5}deg`)
    element.style.setProperty('--ry', `${(event.clientX - box.left - box.width / 2) / box.width * 9}deg`)
  }
  function resetTilt(event: PointerEvent) {
    const element = event.currentTarget as HTMLElement
    element.style.removeProperty('--rx'); element.style.removeProperty('--ry')
  }
  function drawField() {
    const ctx = context
    if (!ctx) return
    const dark = theme.value === 'dark', radius = Math.min(width * .44, 650)
    ctx.clearRect(0, 0, width, height)
    for (let ring = 0; ring < 4; ring++) {
      const rx = radius + ring * 34, ry = height * (.27 + ring * .025)
      ctx.save(); ctx.translate(width / 2, height * .53); ctx.rotate(-.1)
      ctx.beginPath(); ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2)
      ctx.strokeStyle = dark ? `rgba(121,170,255,${.3 - ring * .045})` : `rgba(21,89,214,${.27 - ring * .04})`
      ctx.lineWidth = ring ? .65 : 1.2; ctx.stroke()
      const phase = lightTime * .00022 + ring * 1.7
      ctx.beginPath(); ctx.ellipse(0, 0, rx, ry, 0, phase, phase + .28)
      ctx.strokeStyle = dark ? '#b7d5ff' : '#1559d6'
      ctx.lineWidth = ring ? 1.6 : 2.2; ctx.stroke(); ctx.restore()
    }
  }
  function resizeField() {
    if (!canvas || !context) return
    const bounds = canvas.parentElement!.getBoundingClientRect()
    width = bounds.width; height = bounds.height
    const ratio = Math.min(window.devicePixelRatio || 1, 1.5)
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio)
    context.setTransform(ratio, 0, 0, ratio, 0, 0); drawField()
  }
  function running() { return mounted && !stopped.value && !backgrounded.value && visible }
  function tick(now: number) {
    frame = 0
    if (!running()) return
    const delta = lastFrame ? Math.min(now - lastFrame, 100) : 0
    lastFrame = now; lightTime += delta
    // Do not replace a product while the visitor is reading or using its controls.
    if (!hovering && !focused) { elapsed += delta; if (elapsed >= 6500) selectProduct(product.value + 1) }
    drawField(); frame = requestAnimationFrame(tick)
  }
  function syncMotion() {
    if (frame) cancelAnimationFrame(frame)
    frame = 0; lastFrame = 0
    if (stopped.value) {
      const orbit = root.value?.querySelector<HTMLElement>('.orbit-system')
      orbit?.style.removeProperty('--rx'); orbit?.style.removeProperty('--ry')
    }
    drawField()
    if (running()) frame = requestAnimationFrame(tick)
  }
  function updateScroll() {
    scrollFrame = 0
    if (stopped.value || mobile || manualStage) return
    const section = root.value?.querySelector<HTMLElement>('.creation')
    if (!section) return
    const bounds = section.getBoundingClientRect()
    if (bounds.top > innerHeight || bounds.bottom < 0) return
    const progress = Math.max(0, Math.min(1, -bounds.top / Math.max(1, bounds.height - innerHeight)))
    stage.value = Math.min(2, Math.floor(progress * 3))
  }
  watch(stopped, syncMotion)
  watch(theme, drawField)
  onMounted(() => {
    mounted = true
    const element = root.value!
    function listen(target: EventTarget, event: string, handler: EventListener) {
      target.addEventListener(event, handler, { passive: true })
      cleanup.push(() => target.removeEventListener(event, handler))
    }
    canvas = element.querySelector<HTMLCanvasElement>('#field')
    // Missing Canvas support removes only decorative rails, never the product stage.
    if (canvas && typeof CanvasRenderingContext2D !== 'undefined') context = canvas.getContext('2d')
    if (typeof matchMedia === 'function') {
      const preference = matchMedia('(prefers-reduced-motion: reduce)'), size = matchMedia('(max-width: 760px)')
      const preferences = () => { reduced.value = preference.matches; mobile = size.matches; syncMotion(); updateScroll() }
      listen(preference, 'change', preferences); listen(size, 'change', preferences); preferences()
    }
    const visibility = () => { backgrounded.value = document.hidden; syncMotion() }
    listen(document, 'visibilitychange', visibility)
    listen(window, 'scroll', () => { if (!scrollFrame) scrollFrame = requestAnimationFrame(updateScroll) })
    listen(window, 'resize', () => { resizeField(); updateScroll() })
    const field = element.querySelector<HTMLElement>('.lightfield')!
    listen(field, 'pointerenter', event => { if ((event as PointerEvent).pointerType === 'mouse') hovering = true })
    listen(field, 'pointerleave', () => { hovering = false })
    listen(field, 'focusin', () => { focused = true })
    listen(field, 'focusout', event => { focused = field.contains((event as FocusEvent).relatedTarget as Node | null) })
    if (typeof ResizeObserver !== 'undefined') {
      const resize = new ResizeObserver(resizeField)
      resize.observe(field); cleanup.push(() => resize.disconnect())
    }
    if (typeof IntersectionObserver !== 'undefined') {
      const observer = new IntersectionObserver(entries => {
        for (const entry of entries) {
          entry.target.classList.toggle('offscreen', !entry.isIntersecting)
          if (entry.target === field) { visible = entry.isIntersecting; syncMotion() }
        }
      })
      element.querySelectorAll('.home-main > section,.lightfield').forEach(section => observer.observe(section))
      cleanup.push(() => observer.disconnect())
    }
    resizeField(); visibility(); updateScroll()
  })
  onUnmounted(() => {
    mounted = false
    cancelAnimationFrame(frame); cancelAnimationFrame(scrollFrame)
    cleanup.forEach(dispose => dispose())
    context = null; canvas = null
  })
  return { paused, reduced, stopped, backgrounded, product, stage, slot, selectProduct, selectStage, galleryKey, tilt, resetTilt }
}
