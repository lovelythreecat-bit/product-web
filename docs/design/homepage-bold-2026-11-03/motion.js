(() => {
  const root = document.documentElement;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const mobile = matchMedia('(max-width: 760px)');
  const motionButton = document.querySelector('#motion');
  let paused = false, active = 0, stage = 0, manualStage = false, elapsed = 0;
  let visibleHero = true, lastFrame = 0, frame = 0, lightTime = 0;
  const hero = document.querySelector('.hero');
  const field = document.querySelector('.lightfield');
  const canvas = document.querySelector('#field');
  const ctx = canvas.getContext('2d');
  const orbit = document.querySelector('.orbit-system');
  const creation = document.querySelector('.creation');
  const stageElement = document.querySelector('.creation-stage');
  const categories = [...document.querySelectorAll('[data-select]')];
  const planes = [...document.querySelectorAll('[data-product]')];
  let width = 0, height = 0;
  function stopped() { return paused || reduced.matches; }
  function selectProduct(value) {
    active = (value + 3) % 3; elapsed = 0;
    planes.forEach((plane, i) => { plane.dataset.slot = String((i - active + 3) % 3); });
    categories.forEach((button, i) => button.setAttribute('aria-pressed', String(i === active)));
  }
  categories.forEach((button, i) => button.addEventListener('click', () => selectProduct(i)));
  orbit.addEventListener('keydown', event => {
    if (!['ArrowRight','ArrowLeft','Home','End'].includes(event.key)) return;
    event.preventDefault();
    selectProduct(event.key === 'Home' ? 0 : event.key === 'End' ? 2 : active + (event.key === 'ArrowRight' ? 1 : -1));
  });
  orbit.addEventListener('pointermove', event => {
    if (stopped() || event.pointerType !== 'mouse') return;
    const box = orbit.getBoundingClientRect();
    orbit.style.setProperty('--rx', `${-(event.clientY - box.top - box.height / 2) / box.height * 5}deg`);
    orbit.style.setProperty('--ry', `${(event.clientX - box.left - box.width / 2) / box.width * 9}deg`);
  });
  orbit.addEventListener('pointerleave', () => { orbit.style.setProperty('--rx','0deg'); orbit.style.setProperty('--ry','0deg'); });
  function selectStage(value) {
    stage = value; stageElement.dataset.stage = String(stage);
    document.querySelectorAll('[data-step]').forEach((button, i) => button.setAttribute('aria-pressed', String(i === stage)));
    document.querySelectorAll('.scene').forEach((scene, i) => { scene.inert = i !== stage; scene.setAttribute('aria-hidden', String(i !== stage)); });
  }
  document.querySelectorAll('[data-step]').forEach((button, i) => button.addEventListener('click', () => { manualStage = true; selectStage(i); }));
  function scrollScene() {
    if (stopped() || mobile.matches || manualStage) return;
    const bounds = creation.getBoundingClientRect();
    if (bounds.top > innerHeight || bounds.bottom < 0) return;
    const progress = Math.max(0, Math.min(1, -bounds.top / Math.max(1, bounds.height - innerHeight)));
    const next = Math.min(2, Math.floor(progress * 3));
    if (next !== stage) selectStage(next);
  }
  let scrollFrame = 0;
  addEventListener('scroll', () => { if (!scrollFrame) scrollFrame = requestAnimationFrame(() => { scrollFrame = 0; scrollScene(); }); }, {passive:true});
  function sizeField() {
    const rect = field.getBoundingClientRect(); width = rect.width; height = rect.height;
    const ratio = Math.min(devicePixelRatio || 1, 1.5);
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    ctx?.setTransform(ratio,0,0,ratio,0,0); drawField();
  }
  function drawField() {
    if (!ctx) return;
    const dark = root.dataset.theme === 'dark';
    ctx.clearRect(0,0,width,height);
    const centerX = width / 2, centerY = height * .53;
    const radius = Math.min(width * .44, 650);
    // Three projected production rails: restrained continuous geometry, no random particles.
    for (let ring = 0; ring < 4; ring++) {
      const rx = radius + ring * 34, ry = height * (.27 + ring * .025);
      ctx.save(); ctx.translate(centerX,centerY); ctx.rotate(-.1);
      ctx.beginPath(); ctx.ellipse(0,0,rx,ry,0,0,Math.PI*2);
      ctx.strokeStyle = dark ? `rgba(121,170,255,${.3-ring*.045})` : `rgba(21,89,214,${.27-ring*.04})`;
      ctx.lineWidth = ring ? .65 : 1.2; ctx.stroke();
      const phase = lightTime * .00022 + ring * 1.7;
      ctx.beginPath(); ctx.ellipse(0,0,rx,ry,0,phase,phase+.28);
      ctx.strokeStyle = dark ? '#b7d5ff' : '#1559d6'; ctx.lineWidth = ring ? 1.6 : 2.2; ctx.stroke();
      ctx.restore();
    }
  }
  function tick(now) {
    frame = 0;
    const delta = lastFrame ? Math.min(now-lastFrame,80) : 0; lastFrame = now;
    if (!stopped() && !document.hidden && visibleHero) {
      lightTime += delta; elapsed += delta;
      if (elapsed > 6500) selectProduct(active + 1);
      drawField(); frame = requestAnimationFrame(tick);
    }
  }
  function syncMotion() {
    document.body.classList.toggle('paused', stopped());
    motionButton.disabled = reduced.matches;
    motionButton.textContent = reduced.matches ? '系统已减少动效' : paused ? '开启动效' : '暂停动效';
    motionButton.setAttribute('aria-pressed',String(stopped()));
    if (frame) cancelAnimationFrame(frame);
    frame = 0; lastFrame = 0;
    document.querySelectorAll('main>section').forEach(section => section.classList.toggle('offscreen',document.hidden || section.getBoundingClientRect().bottom <= 0 || section.getBoundingClientRect().top >= innerHeight));
    drawField();
    if (!stopped() && visibleHero && !document.hidden) frame = requestAnimationFrame(tick);
  }
  motionButton.addEventListener('click', () => { paused = !paused; syncMotion(); });
  reduced.addEventListener('change',syncMotion);
  document.addEventListener('visibilitychange',syncMotion);
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      entry.target.classList.toggle('offscreen',!entry.isIntersecting || document.hidden);
      if (entry.target === hero) { visibleHero = entry.isIntersecting; syncMotion(); }
    });
  },{threshold:0});
  document.querySelectorAll('main>section').forEach(section => observer.observe(section));
  new ResizeObserver(sizeField).observe(field);
  const themeButton = document.querySelector('#theme');
  function setTheme(theme) {
    root.dataset.theme = theme;
    themeButton.setAttribute('aria-label', theme === 'dark' ? '切换为浅色主题' : '切换为深色主题');
    drawField();
  }
  themeButton.addEventListener('click', () => setTheme(root.dataset.theme === 'dark' ? 'light' : 'dark'));
  setTheme(new URLSearchParams(location.search).get('theme') === 'light' ? 'light' : 'dark');
  const guidance = ['卡在哪一步，玲玲就在哪一步。','主图、详情、海报，输入即出。','每一步都有人陪你走完，再也不怕「不会用」。','生成即分发。'];
  document.querySelectorAll('[data-guide]').forEach((button,i) => button.addEventListener('click',() => {
    document.querySelector('#guide-speech').textContent = guidance[i];
    document.querySelectorAll('[data-guide]').forEach((item,j) => item.setAttribute('aria-pressed',String(i === j)));
  }));
  document.querySelectorAll('[data-workspace]').forEach(button => button.addEventListener('click',() => {
    const pro = button.dataset.workspace === 'pro';
    document.querySelectorAll('[data-workspace]').forEach(item => item.setAttribute('aria-pressed',String(item === button)));
    document.querySelector('#workspace-title').textContent = pro ? '想要完全掌控？' : '零基础，对话即出片';
    document.querySelector('#workspace-copy').textContent = pro ? '想要完全掌控？专业工作台给你图层、参数、批量与模板。飞马不替你决定，只让你更快。' : '专业工作台给老手完整控制权；小白工作台把专业能力收进一句对话——选品类、说卖点、挑风格，智能体替你排兵布阵，零基础也能出品专业级素材。';
    document.querySelector('#workspace-prompt').textContent = pro ? '飞马不替你决定，只让你更快。' : '我要卖一款保温杯，主打上班通勤';
    document.querySelector('.pro-options').hidden = !pro;
  }));
  selectProduct(0); selectStage(0); sizeField(); syncMotion();
})();
