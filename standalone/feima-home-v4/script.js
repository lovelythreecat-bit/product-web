(() => {
  'use strict';

  const carousel = document.querySelector('.carousel');
  const tabs = Array.from(document.querySelectorAll('[data-slide]'));
  const panes = Array.from(document.querySelectorAll('.hero-pane'));
  const pauseButton = document.getElementById('carousel-pause');
  const announcement = document.getElementById('carousel-announcement');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const duration = 5000;
  let current = 0;
  let elapsed = 0;
  let lastFrame = null;
  let frameId = null;
  let userPaused = reducedMotion.matches;
  let onScreen = true;
  const paneAnimations = new Map();
  const motionAnimations = new Set();
  const ease = 'cubic-bezier(.16,1,.3,1)';

  function animateOnce(element, frames, options) {
    if (reducedMotion.matches || !element.animate) return null;
    const animation = element.animate(frames, options);
    motionAnimations.add(animation);
    const forget = () => motionAnimations.delete(animation);
    animation.addEventListener('finish', forget, { once: true });
    animation.addEventListener('cancel', forget, { once: true });
    return animation;
  }

  function settlePanes() {
    paneAnimations.forEach(animation => animation.cancel());
    paneAnimations.clear();
    panes.forEach((pane, i) => {
      pane.hidden = i !== current;
      pane.inert = i !== current;
      pane.setAttribute('aria-hidden', String(i !== current));
    });
  }

  function selectSlide(index, { focus = false, announce = false } = {}) {
    const previous = current;
    const outgoingOpacity = getComputedStyle(panes[previous]).opacity;
    current = (index + tabs.length) % tabs.length;
    settlePanes();
    elapsed = 0;
    lastFrame = null;
    tabs.forEach((tab, i) => {
      const selected = i === current;
      tab.classList.toggle('active', selected);
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    if (previous !== current && !reducedMotion.matches && panes[current].animate) {
      const outgoing = panes[previous];
      outgoing.hidden = false;
      const exit = outgoing.animate([
        { opacity: outgoingOpacity, transform: 'translateX(0)' },
        { opacity: 0, transform: 'translateX(-8px)' }
      ], { duration: 240, easing: 'ease-out' });
      paneAnimations.set(outgoing, exit);
      exit.onfinish = () => {
        if (paneAnimations.get(outgoing) !== exit) return;
        outgoing.hidden = true;
        paneAnimations.delete(outgoing);
      };
      const incoming = panes[current];
      const enter = incoming.animate([
        { opacity: 0, transform: 'translateX(12px)' },
        { opacity: 1, transform: 'translateX(0)' }
      ], { duration: 460, easing: ease });
      paneAnimations.set(incoming, enter);
      enter.onfinish = () => paneAnimations.delete(incoming);
    }
    if (focus) tabs[current].focus();
    if (announce) announcement.textContent = `已切换：${tabs[current].querySelector('b').textContent}`;
  }

  function canRun() {
    return !userPaused && !document.hidden && onScreen;
  }

  function tick() {
    frameId = null;
    lastFrame = null;
    if (!canRun()) return;
    selectSlide(current + 1);
    syncTimer();
  }

  function syncTimer() {
    if (frameId !== null) window.clearTimeout(frameId);
    if (lastFrame !== null) elapsed += performance.now() - lastFrame;
    frameId = null;
    lastFrame = null;
    pauseButton.setAttribute('aria-pressed', String(userPaused));
    pauseButton.querySelector('span').textContent = userPaused ? '继续轮播' : '暂停轮播';
    pauseButton.setAttribute('aria-label', userPaused ? '继续自动轮播' : '暂停自动轮播');
    if (canRun()) {
      lastFrame = performance.now();
      frameId = window.setTimeout(tick, Math.max(0, duration - elapsed));
    }
  }

  tabs.forEach((tab, index) => tab.addEventListener('click', () => {
    selectSlide(index, { announce: true });
    syncTimer();
  }));

  carousel.addEventListener('keydown', (event) => {
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
    // Arrow keys belong to this carousel only, never to the rest of the page.
    if (!event.target.closest('[role="tablist"]') && !event.target.closest('[role="tabpanel"]')) return;
    event.preventDefault();
    let index = current;
    if (event.key === 'ArrowRight') index += 1;
    if (event.key === 'ArrowLeft') index -= 1;
    if (event.key === 'Home') index = 0;
    if (event.key === 'End') index = tabs.length - 1;
    selectSlide(index, { focus: true, announce: true });
    syncTimer();
  });

  pauseButton.addEventListener('click', () => {
    userPaused = !userPaused;
    announcement.textContent = userPaused ? '自动轮播已暂停' : '自动轮播已继续';
    syncTimer();
  });
  document.addEventListener('visibilitychange', syncTimer);
  reducedMotion.addEventListener('change', (event) => {
    if (event.matches) {
      userPaused = true;
      settlePanes();
      motionAnimations.forEach(animation => animation.cancel());
    }
    syncTimer();
  });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      onScreen = entry.isIntersecting && entry.intersectionRatio >= 0.1;
      syncTimer();
    }, { threshold: [0, 0.1] }).observe(carousel);
  }
  syncTimer();

  settlePanes();
  const navigation = document.querySelector('.navigation');
  const updateNavigation = () => navigation.classList.toggle('is-scrolled', window.scrollY > 12);
  updateNavigation();
  window.addEventListener('scroll', updateNavigation, { passive: true });

  // One focal sequence: message, action, character, then the working canvas.
  [['.hero-intro h1', 0], ['.hero-actions', 100], ['.hero-ling', 150], ['.carousel', 200]].forEach(([selector, delay]) => {
    animateOnce(document.querySelector(selector), [
      { opacity: .15, transform: 'translateY(16px)' },
      { opacity: 1, transform: 'translateY(0)' }
    ], { duration: 700, delay, easing: ease, fill: 'backwards' });
  });

  // Scroll-linked fade in BOTH directions, confined to the viewport edges.
  // Reading area stays fully opaque; no layout movement or persistent RAF loop.
  const fadeElements = Array.from(document.querySelectorAll('.sec-head,.tria,.defcard,.scene,.case,.feat,.shot,.plan,.adbar,.final-content'));
  fadeElements.forEach(el => el.classList.add('scroll-fade'));
  let scrollFrame = null;
  const smoothStep = value => {
    const t = Math.max(0, Math.min(1, value));
    return t * t * (3 - 2 * t);
  };
  function updateScrollFade() {
    scrollFrame = null;
    const topEdge = navigation.getBoundingClientRect().bottom;
    const bottomEdge = window.innerHeight;
    // Batch layout reads before style writes, including large mobile cards.
    const values = fadeElements.map(el => {
      if (reducedMotion.matches) return 1;
      const rect = el.getBoundingClientRect();
      const band = Math.min(120, (bottomEdge - topEdge) * .16, rect.height * .6);
      if (band <= 0) return 1;
      return smoothStep(Math.min((bottomEdge - rect.top) / band, (rect.bottom - topEdge) / band));
    });
    fadeElements.forEach((el, i) => {
      const value = values[i].toFixed(3);
      if (el.style.getPropertyValue('--scroll-opacity') !== value) el.style.setProperty('--scroll-opacity', value);
    });
  }
  function scheduleScrollFade() {
    if (scrollFrame === null) scrollFrame = requestAnimationFrame(updateScrollFade);
  }
  window.addEventListener('scroll', scheduleScrollFade, { passive: true });
  window.addEventListener('resize', scheduleScrollFade, { passive: true });
  window.addEventListener('load', scheduleScrollFade, { once: true });
  window.addEventListener('pageshow', scheduleScrollFade);
  reducedMotion.addEventListener('change', scheduleScrollFade);
  updateScrollFade();

  const menuToggle = document.getElementById('menu-toggle');
  const navLinks = document.getElementById('nav-links');
  function closeMenu({ restore = false } = {}) {
    navLinks.classList.remove('open');
    menuToggle.setAttribute('aria-expanded', 'false');
    menuToggle.setAttribute('aria-label', '打开导航菜单');
    if (restore) menuToggle.focus();
  }
  menuToggle.addEventListener('click', () => {
    const open = menuToggle.getAttribute('aria-expanded') !== 'true';
    menuToggle.setAttribute('aria-expanded', String(open));
    menuToggle.setAttribute('aria-label', open ? '关闭导航菜单' : '打开导航菜单');
    navLinks.classList.toggle('open', open);
  });
  navLinks.addEventListener('click', (event) => {
    if (event.target.closest('a')) closeMenu();
  });
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.navigation')) closeMenu();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menuToggle.getAttribute('aria-expanded') === 'true') closeMenu({ restore: true });
  });
  window.matchMedia('(min-width: 801px)').addEventListener('change', (event) => {
    if (event.matches) closeMenu();
  });

})();
