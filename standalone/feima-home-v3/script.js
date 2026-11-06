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
  let modalOpen = false;

  function renderProgress() {
    tabs.forEach((tab, index) => {
      tab.querySelector('.tab-progress').style.transform = `scaleX(${index === current ? Math.min(elapsed / duration, 1) : 0})`;
    });
  }

  function selectSlide(index, { focus = false, announce = false } = {}) {
    current = (index + tabs.length) % tabs.length;
    elapsed = 0;
    lastFrame = null;
    tabs.forEach((tab, i) => {
      const selected = i === current;
      tab.classList.toggle('active', selected);
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
      panes[i].hidden = !selected;
    });
    renderProgress();
    if (focus) tabs[current].focus();
    if (announce) announcement.textContent = `已切换：${tabs[current].querySelector('b').textContent}`;
  }

  function canRun() {
    return !userPaused && !document.hidden && onScreen && !modalOpen;
  }

  function tick(now) {
    frameId = null;
    if (!canRun()) { lastFrame = null; return; }
    if (lastFrame !== null) elapsed += now - lastFrame;
    lastFrame = now;
    if (elapsed >= duration) selectSlide(current + 1);
    renderProgress();
    frameId = window.requestAnimationFrame(tick);
  }

  function syncTimer() {
    if (frameId !== null) window.cancelAnimationFrame(frameId);
    frameId = null;
    lastFrame = null;
    pauseButton.setAttribute('aria-pressed', String(userPaused));
    pauseButton.querySelector('span').textContent = userPaused ? '继续轮播' : '暂停轮播';
    pauseButton.setAttribute('aria-label', userPaused ? '继续自动轮播' : '暂停自动轮播');
    if (canRun()) frameId = window.requestAnimationFrame(tick);
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
    if (event.matches) userPaused = true;
    syncTimer();
  });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      onScreen = entry.isIntersecting && entry.intersectionRatio >= 0.1;
      syncTimer();
    }, { threshold: [0, 0.1] }).observe(carousel);
  }
  syncTimer();

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
  window.matchMedia('(min-width: 641px)').addEventListener('change', (event) => {
    if (event.matches) closeMenu();
  });

  const dialog = document.getElementById('preview-dialog');
  const dialogBody = document.getElementById('dialog-body');
  const page = document.getElementById('page-content');
  const closeButton = dialog.querySelector('.dialog-close');
  let restoreFocus = null;
  let scrollPosition = 0;
  let afterCloseTarget = null;
  let currentDemo = 'storyboard';
  const picture = (i, extra = '', label = '') => `<div class="material m${i} ${extra}" ${label ? `role="img" aria-label="${label}"` : 'aria-hidden="true"'}></div>`;
  const demos = {
    storyboard: [
      { image: 2, label: '分镜 1 / 3 · 通勤场景', title: '带上轻便，一起出发', copy: '城市通勤的日常，用一只保温杯把温度带在身边。' },
      { image: 0, label: '分镜 2 / 3 · 商品特写', title: '让商品细节被看见', copy: '银色杯身与简约外观，在画面中清楚呈现。' },
      { image: 1, label: '分镜 3 / 3 · 生活场景', title: '日常好物，自然融入生活', copy: '从上班通勤到桌面一角，完成一组连贯的商品表达。' }
    ],
    demo: [
      { image: 0, label: '功能演示 1 / 3 · 准备商品', title: '从一张商品图开始', copy: '告诉飞马：「我要卖一款保温杯，主打上班通勤」，把想法变成创作方向。' },
      { image: 10, label: '功能演示 2 / 3 · 对话创作', title: '玲玲陪你选风格、出图与微调', copy: '小白用对话表达想法；老手使用图层、参数、批量与模板，掌握更多创作细节。' },
      { image: 11, label: '功能演示 3 / 3 · 查看成果', title: '一套创意，多种营销表达', copy: '查看主图、场景海报与短视频分镜，了解同一款商品的多种呈现方式。' }
    ]
  };

  function showDialog(html) {
    if (dialog.open) {
      dialogBody.innerHTML = html;
      dialog.scrollTop = 0;
      closeButton.focus({ preventScroll: true });
      return;
    }
    restoreFocus = document.activeElement;
    scrollPosition = window.scrollY;
    dialogBody.innerHTML = html;
    modalOpen = true;
    syncTimer();
    dialog.showModal();
    page.inert = true;
    document.body.style.overflow = 'hidden';
    dialog.scrollTop = 0;
    closeButton.focus({ preventScroll: true });
  }

  function closeDialog() {
    if (!dialog.open) return;
    dialog.close();
  }

  dialog.addEventListener('close', () => {
    page.inert = false;
    document.body.style.overflow = '';
    modalOpen = false;
    syncTimer();
    window.scrollTo({ top: scrollPosition, behavior: 'instant' });
    if (restoreFocus && restoreFocus.isConnected) restoreFocus.focus({ preventScroll: true });
    if (afterCloseTarget) {
      afterCloseTarget.scrollIntoView({ behavior: reducedMotion.matches ? 'instant' : 'smooth', block: 'start' });
      afterCloseTarget = null;
    }
  });
  closeButton.addEventListener('click', closeDialog);
  dialog.addEventListener('cancel', (event) => { event.preventDefault(); closeDialog(); });
  dialog.addEventListener('click', (event) => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) closeDialog();
  });
  dialog.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab') return;
    const focusables = Array.from(dialog.querySelectorAll('button,a[href],[tabindex="0"]')).filter(el => !el.disabled && !el.hidden);
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });

  function showDemo(type) {
    currentDemo = type;
    const isVideo = type === 'storyboard';
    showDialog(`<h2 id="dialog-title">${isVideo ? '保温杯 · 通勤种草分镜' : '看飞马如何创作'}</h2><p id="dialog-description">${isVideo ? '这是本地静态分镜演示。点击下方步骤查看画面与说明；这里没有视频文件或真实视频播放。' : '这是独立预览中的本地功能演示。点击步骤了解商品从想法到成果的过程，不会调用 AI 或提交生成任务。'}</p><div class="demo-stage"><div class="demo-image" id="demo-image"></div><div class="demo-caption" id="demo-caption" aria-live="polite"></div></div><div class="demo-steps" role="group" aria-label="${isVideo ? '查看分镜' : '查看演示步骤'}">${demos[type].map((_, i) => `<button class="demo-step" data-demo-step="${i}" aria-pressed="${i === 0}">${isVideo ? ['通勤场景', '商品特写', '生活场景'][i] : ['准备商品', '对话创作', '查看成果'][i]}</button>`).join('')}</div><p class="dialog-note">画面为创作示例，未连接真实生成、店铺发布或经营数据。</p>`);
    setDemoStep(0);
  }

  function setDemoStep(index) {
    const step = demos[currentDemo][index];
    if (!step) return;
    document.getElementById('demo-image').innerHTML = picture(step.image, '', step.title) + `<span class="demo-label">${step.label}</span>`;
    document.getElementById('demo-caption').innerHTML = `<h3>${step.title}</h3><p>${step.copy}</p>`;
    dialog.querySelectorAll('[data-demo-step]').forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
  }

  function showInfo(action, trigger) {
    const copy = {
      trial: ['先看见你的第一组好作品', '这是独立首页预览，暂未接入注册或账户系统。你可以先浏览作品，或查看本地创作演示；此操作不会创建账户。'],
      standard: ['标准版 · ¥99 / 月', '当前展示的是原稿套餐示意。独立预览未接入订阅或支付，此操作不会开通套餐，也不会产生付款。可以先浏览作品，了解创作表现。'],
      consult: ['一起找到合适的创作方案', '独立预览暂未接入顾问联系通道，此操作没有发送消息或提交联系资料。你可以先查看作品与本地演示，了解旗舰版的创作方向。'],
      lingling: ['玲玲，陪你从想法到出片', '这是玲玲数字人的独立展示预览，尚未接入实时 AI 客服。现在可以通过本地功能演示，看看她如何陪你选风格、出图、微调与发布。'],
      resource: [trigger.textContent.trim(), '此独立预览尚未接入该服务或内容页面。你可以继续浏览创作场景、作品展示和套餐说明；此操作不会跳转至业务系统。']
    };
    const [title, description] = copy[action];
    showDialog(`<h2 id="dialog-title">${title}</h2><p id="dialog-description">${description}</p><div class="dialog-actions"><button class="button button-primary" data-modal-action="works">浏览作品</button><button class="dialog-link" data-modal-action="demo">查看本地演示</button></div>`);
  }

  document.addEventListener('click', (event) => {
    const stepButton = event.target.closest('[data-demo-step]');
    if (stepButton) { setDemoStep(Number(stepButton.dataset.demoStep)); return; }
    const modalAction = event.target.closest('[data-modal-action]');
    if (modalAction) {
      if (modalAction.dataset.modalAction === 'works') {
        afterCloseTarget = document.getElementById('works');
        closeDialog();
      } else {
        // Reuse the open dialog so its original return focus and isolation remain intact.
        showDemo('demo');
      }
      return;
    }
    const trigger = event.target.closest('[data-action]');
    if (!trigger) return;
    event.preventDefault();
    const action = trigger.dataset.action;
    if (action === 'demo' || action === 'storyboard') { showDemo(action); return; }
    if (action === 'image-main' || action === 'image-scene') {
      const mainImage = action === 'image-main';
      const title = mainImage ? '保温杯 · 电商主图' : '保温杯 · 种草海报';
      showDialog(`<h2 id="dialog-title">${title}</h2><p id="dialog-description">${mainImage ? '文生图 · 白底主图' : '文生图 · 场景海报'}，创作示例。</p>${picture(mainImage ? 0 : 1, 'dialog-art', title)}`);
      return;
    }
    showInfo(action, trigger);
  });
})();
