import { computed, onMounted, onUnmounted, ref, watch, type Ref } from 'vue'

/** All animation resources belong to this route and are released on navigation. */
export function useHomepageMotion(root: Ref<HTMLElement | undefined>) {
  const paused = ref(false)
  const reduced = ref(false)
  const backgrounded = ref(false)
  const stopped = computed(() => paused.value || reduced.value)
  const product = ref(0)
  const autoStopped = ref(false)
  const cycleProgress = ref(0)
  const stage = ref(0)
  const touring = ref(false)
  const galleryRunning = ref(false)
  let mobile = false, visible = true, hovering = false, focused = false
  let cycleFrame = 0, scrollFrame = 0, lastFrame = 0, elapsed = 0, manualY = -1
  let tour: ReturnType<typeof setInterval> | undefined
  const cleanup: (() => void)[] = []

  function slot(index: number) { return ['active', 'next', 'previous'][(index - product.value + 3) % 3] }
  function selectProduct(index: number, manual = true) {
    product.value = (index + 3) % 3
    elapsed = 0
    cycleProgress.value = 0
    if (manual) autoStopped.value = true
    syncCycle()
  }
  function stopTour() {
    if (tour !== undefined) clearInterval(tour)
    tour = undefined
    touring.value = false
  }
  function selectStage(index: number) {
    stopTour()
    manualY = window.scrollY
    stage.value = index
  }
  function playStory() {
    if (touring.value) { stopTour(); return }
    manualY = window.scrollY
    if (stopped.value) { stage.value = (stage.value + 1) % 3; return }
    stage.value = 0
    touring.value = true
    let advances = 0
    tour = setInterval(() => {
      stage.value = (stage.value + 1) % 3
      if (++advances === 5) stopTour()
    }, 3500)
  }
  function syncCycle() {
    const autoFocused = root.value?.querySelector('.gallery-auto') === document.activeElement
    const running = !stopped.value && !backgrounded.value && !autoStopped.value && visible && !hovering && (!focused || autoFocused)
    galleryRunning.value = running
    if (running && !cycleFrame) {
      lastFrame = performance.now()
      cycleFrame = requestAnimationFrame(cycle)
    } else if (!running && cycleFrame) {
      cancelAnimationFrame(cycleFrame)
      cycleFrame = 0
    }
  }
  function cycle(now: number) {
    elapsed += Math.min(now - lastFrame, 100)
    lastFrame = now
    if (elapsed >= 6500) { product.value = (product.value + 1) % 3; elapsed = 0 }
    cycleProgress.value = elapsed / 6500
    cycleFrame = requestAnimationFrame(cycle)
  }
  function galleryKey(event: KeyboardEvent) {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    selectProduct(product.value + (event.key === 'ArrowRight' ? 1 : -1))
  }
  function updateScroll() {
    scrollFrame = 0
    const story = root.value?.querySelector<HTMLElement>('.story')
    const screen = root.value?.querySelector<HTMLElement>('.story-screen')
    if (!story || !screen) return
    if (stopped.value || mobile) { screen.style.removeProperty('--screen-rotate'); return }
    const progress = Math.max(0, Math.min(.999, (80 - story.getBoundingClientRect().top) / Math.max(1, story.offsetHeight - innerHeight)))
    if (manualY >= 0 && Math.abs(window.scrollY - manualY) > 100) { manualY = -1; stopTour() }
    if (manualY < 0 && !touring.value) stage.value = Math.min(2, Math.floor(progress * 3))
    screen.style.setProperty('--screen-rotate', `${(1 - progress) * -7}deg`)
  }
  function tilt(event: PointerEvent, stageTilt = false) {
    if (event.pointerType !== 'mouse' || stopped.value || mobile) return
    const element = event.currentTarget as HTMLElement
    const rect = element.getBoundingClientRect()
    element.style.setProperty(stageTilt ? '--stage-rx' : '--rx', `${-(event.clientY - rect.top - rect.height / 2) / rect.height * 5}deg`)
    element.style.setProperty(stageTilt ? '--stage-ry' : '--ry', `${(event.clientX - rect.left - rect.width / 2) / rect.width * 7}deg`)
  }
  function resetTilt(event: PointerEvent) {
    const element = event.currentTarget as HTMLElement
    for (const key of ['--rx', '--ry', '--stage-rx', '--stage-ry']) element.style.removeProperty(key)
  }
  watch([stopped, autoStopped], () => { if (stopped.value) stopTour(); syncCycle(); updateScroll() })
  onMounted(() => {
    const element = root.value!
    function listen(target: EventTarget, name: string, handler: EventListener) {
      target.addEventListener(name, handler, { passive: true })
      cleanup.push(() => target.removeEventListener(name, handler))
    }
    if (typeof matchMedia === 'function') {
      const preference = matchMedia('(prefers-reduced-motion: reduce)')
      const size = matchMedia('(max-width: 760px)')
      const preferences = () => { reduced.value = preference.matches; mobile = size.matches; updateScroll(); syncCycle() }
      listen(preference, 'change', preferences)
      listen(size, 'change', preferences)
      preferences()
    }
    listen(window, 'scroll', () => { if (!scrollFrame) scrollFrame = requestAnimationFrame(updateScroll) })
    listen(window, 'resize', updateScroll)
    const visibility = () => { backgrounded.value = document.hidden; if (backgrounded.value) stopTour(); syncCycle() }
    listen(document, 'visibilitychange', visibility)
    const showcase = element.querySelector<HTMLElement>('.hero-showcase')!
    listen(showcase, 'pointerenter', event => { if ((event as PointerEvent).pointerType === 'mouse') { hovering = true; syncCycle() } })
    listen(showcase, 'pointerleave', () => { hovering = false; syncCycle() })
    listen(showcase, 'focusin', () => { focused = true; syncCycle() })
    listen(showcase, 'focusout', event => { focused = showcase.contains((event as FocusEvent).relatedTarget as Node | null); syncCycle() })
    if (typeof IntersectionObserver !== 'undefined') {
      const reveals = new IntersectionObserver(entries => entries.forEach(entry => {
        if (entry.isIntersecting) { entry.target.classList.add('seen'); reveals.unobserve(entry.target) }
      }), { threshold: .12 })
      element.querySelectorAll('.reveal').forEach(item => reveals.observe(item))
      const visibilityObserver = new IntersectionObserver(entries => entries.forEach(entry => {
        entry.target.classList.toggle('offscreen', !entry.isIntersecting)
        if (entry.target === showcase) { visible = entry.isIntersecting; syncCycle() }
        if (entry.target.classList.contains('story-screen') && !entry.isIntersecting) stopTour()
      }), { rootMargin: '100px' })
      element.querySelectorAll('.hero-showcase,.lingling-invite,.story-screen,.reel,.character-stage,.delivery-diagram').forEach(item => visibilityObserver.observe(item))
      cleanup.push(() => { reveals.disconnect(); visibilityObserver.disconnect() })
    }
    visibility()
    updateScroll()
  })
  onUnmounted(() => {
    stopTour()
    cancelAnimationFrame(cycleFrame)
    cancelAnimationFrame(scrollFrame)
    cleanup.forEach(dispose => dispose())
  })
  return { paused, reduced, stopped, backgrounded, product, autoStopped, cycleProgress, stage, touring, galleryRunning, slot, selectProduct, selectStage, playStory, galleryKey, tilt, resetTilt }
}
