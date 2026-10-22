(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)')
  const toggle = document.querySelector('#motion-toggle')
  const replay = document.querySelector('#motion-replay')
  let paused = false
  const videos = []
  const entrances = new Set()
  const visible = new Set()
  const pauseIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h4v16H6zm8 0h4v16h-4z"/></svg>'
  const playIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 4 14 8-14 8z"/></svg>'
  document.querySelectorAll('.home-output--video .home-product-visual, #creation-video .home-product-visual').forEach(container => {
    const video = document.createElement('video')
    video.className = 'motion-video'
    video.src = './assets/headphones-loop.mp4'
    video.poster = './assets/headphones-poster.jpg'
    video.muted = true
    video.loop = true
    video.playsInline = true
    video.preload = 'metadata'
    video.setAttribute('aria-label', '耳机创作示例：缓慢推近与平移的循环画面')
    container.replaceChildren(video)
    videos.push(video)
  })
  document.querySelector('.home-cover-label').textContent = '循环预览'
  const caption = document.querySelector('.home-film-caption')
  caption.lastChild.textContent = '动态创作示例'
  const filmButton = document.createElement('button')
  filmButton.className = 'film-toggle'
  filmButton.type = 'button'
  filmButton.innerHTML = pauseIcon
  filmButton.setAttribute('aria-label', '暂停视频示例')
  document.querySelector('#creation-video .home-media-sample').append(filmButton)
  const mainVideo = videos[1]
  let filmPaused = false
  function sync() {
    const stopped = paused || reduced.matches || document.hidden
    document.body.classList.toggle('motion-paused', paused || reduced.matches)
    document.body.classList.toggle('page-hidden', document.hidden)
    toggle.textContent = reduced.matches ? '已减少动态效果' : paused ? '播放动效' : '暂停动效'
    toggle.disabled = reduced.matches
    toggle.setAttribute('aria-pressed', String(paused || reduced.matches))
    replay.disabled = reduced.matches
    filmButton.disabled = reduced.matches || paused
    for (const a of entrances) { if (stopped) a.pause(); else a.play() }
    for (const video of videos) {
      if (stopped || !visible.has(video) || (video === mainVideo && filmPaused)) video.pause()
      else video.play().catch(() => {})
    }
    filmButton.innerHTML = mainVideo.paused ? playIcon : pauseIcon
    filmButton.setAttribute('aria-label', reduced.matches ? '系统已减少动态效果' : mainVideo.paused ? '播放视频示例' : '暂停视频示例')
  }
  function entrance(elements, stagger = 70) {
    if (paused || reduced.matches || document.hidden) return
    elements.forEach((el, index) => {
      const animation = el.animate([{ opacity: .2, translate: '0 14px' }, { opacity: 1, translate: '0 0' }], { duration: 620, delay: Math.min(index * stagger, 210), easing: 'cubic-bezier(.16,1,.3,1)', fill: 'backwards' })
      entrances.add(animation)
      animation.onfinish = () => entrances.delete(animation)
    })
  }
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      entry.target.classList.toggle('is-visible', entry.isIntersecting)
      if (entry.isIntersecting) visible.add(entry.target)
      else visible.delete(entry.target)
      if (entry.isIntersecting && entry.target.matches('.home-creation-grid,.home-scenario-grid') && !entry.target.dataset.revealed) {
        entry.target.dataset.revealed = 'true'
        entrance([...entry.target.children])
      }
    }
    sync()
  }, { threshold: .15 })
  document.querySelectorAll('.home-hero-stage,.home-creation-grid,.home-scenario-grid,video').forEach(el => observer.observe(el))
  toggle.addEventListener('click', () => { paused = !paused; sync() })
  filmButton.addEventListener('click', () => { filmPaused = !filmPaused; sync() })
  mainVideo.addEventListener('play', () => { filmButton.innerHTML = pauseIcon; filmButton.setAttribute('aria-label', '暂停视频示例') })
  mainVideo.addEventListener('pause', () => { filmButton.innerHTML = playIcon; filmButton.setAttribute('aria-label', '播放视频示例') })
  function heroEntrance() { entrance([...document.querySelectorAll('.home-hero-tagline,.home-hero h1,.home-hero-lead,.home-hero-actions')]) }
  replay.addEventListener('click', () => {
    paused = false
    for (const a of entrances) a.cancel()
    entrances.clear()
    window.scrollTo({ top: 0, behavior: 'instant' })
    for (const video of videos) video.currentTime = 0
    document.querySelectorAll('.home-output').forEach(el => el.getAnimations().forEach(a => { a.currentTime = 0 }))
    sync()
    heroEntrance()
  })
  reduced.addEventListener('change', () => {
    if (reduced.matches) { for (const a of entrances) a.cancel(); entrances.clear() }
    sync()
  })
  document.addEventListener('visibilitychange', sync)
  sync()
  heroEntrance()
})()
