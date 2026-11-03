<script setup lang="ts">
import { nextTick, ref } from 'vue'
import FairyIcon from './FairyIcon.vue'
import FairyArtwork from './FairyArtwork.vue'
import heroArtwork from '../../../assets/customer-service/hero.png'
import './customer-service.css'

const input = ref('')
const inputElement = ref<HTMLInputElement>()
const conversation = ref<HTMLDivElement>()
const messages = ref<{ role: 'user' | 'assistant'; text: string; id: number }[]>([
  { id: 0, role: 'user', text: '第一次使用，不知道从哪里开始。' },
  { id: 1, role: 'assistant', text: '别担心，告诉我你的目标，我陪你一步步完成。' },
])
let nextId = 2
const questions = [
  { icon: 'book', text: '如何开始使用？', answer: '从创作工作台开始吧。准备好商品名称、卖点和参考图片，再选择文案、图片或视频创作。提交前记得确认内容与费用。' },
  { icon: 'star', text: '下一步怎么操作？', answer: '使用快速生成时，可以依次确认商品资料、营销文案、图片和视频。每一步先查看结果、确认满意，再继续下一步。' },
  { icon: 'shield', text: '还有其他问题', answer: '你可以试着问我“怎样写文案”“怎样生成图片”或“在哪里查看作品”。这里是互动演示，提供基础使用指引，暂未连接实时客服。' },
] as const

function replyFor(question: string) {
  const preset = questions.find(item => item.text === question)
  if (preset) return preset.answer
  if (/作品|下载/.test(question)) return '生成完成后，可以进入“我的作品”，查看、预览和下载成果。也可以按创作类型筛选，找到需要的内容。'
  if (/文案/.test(question)) return '先准备商品名称、特点和卖点，在创作工作台选择文案创作，填写你想表达的内容。确认本次费用后，就可以开始创作。'
  if (/图片|主图|详情图/.test(question)) return '带上商品参考图片和介绍，选择图片创作，再填写画面要求。可用类型和费用以工作台实际展示为准。'
  if (/视频/.test(question)) return '准备商品介绍和参考图片，进入视频创作。先确认方案，再开始生成，完成后可以预览和下载。'
  if (/开始|使用|新手/.test(question)) return questions[0].answer
  if (/下一步|操作/.test(question)) return questions[1].answer
  return '这里是玲玲的互动演示，暂时只能回答基础使用问题。你可以问我如何开始创作、生成图片或查看作品，也可以点击下方入口前往创作工作台。'
}
function scrollBehavior(): ScrollBehavior {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
}
async function focusConversation() {
  await nextTick()
  document.getElementById('companionship')?.scrollIntoView({ behavior: scrollBehavior(), block: 'center' })
  inputElement.value?.focus({ preventScroll: true })
}
async function ask(question: string) {
  const text = question.trim().slice(0, 300)
  if (!text) return
  messages.value = [...messages.value.slice(-18),
    { id: nextId++, role: 'user', text },
    { id: nextId++, role: 'assistant', text: replyFor(text) },
  ]
  input.value = ''
  await nextTick()
  if (conversation.value) conversation.value.scrollTop = conversation.value.scrollHeight
}
async function askQuickQuestion(question: string) {
  await ask(question)
  await focusConversation()
}
function handleEnter(event: KeyboardEvent) {
  if (event.isComposing) event.preventDefault()
}
</script>

<template>
  <div id="fairy-top" class="fairy-page">
    <div class="fairy-opening">
      <img class="fairy-hero-background" :src="heroArtwork" alt="银发少女玲玲与白色独角飞马，在彩虹与云端城堡间迎接你" width="1536" height="1024" fetchpriority="high" />
      <header class="fairy-header fairy-wrap">
        <a class="fairy-brand" href="#fairy-top" aria-label="玲玲 AI 客服，返回顶部"><FairyIcon name="wing" /><span>玲玲 AI 客服</span></a>
        <nav aria-label="客服特色"><a href="#companionship">梦幻陪伴</a><a href="#guidance">智能引导</a><a href="#interface">童话界面</a><a href="#memory">专属记忆</a></nav>
        <button class="fairy-button fairy-button--small" type="button" @click="focusConversation">开始对话</button>
      </header>
      <section class="fairy-hero fairy-wrap" aria-labelledby="fairy-title">
        <div class="fairy-hero-copy"><h1 id="fairy-title">玲玲的<br />童话 AI 客服</h1><p class="fairy-hero-subtitle">让智能服务像童话一样温暖</p><p class="fairy-hero-description">温柔回应每一个问题，陪你找到下一步。</p><div class="fairy-hero-actions"><button class="fairy-button" type="button" @click="focusConversation">立即体验</button><a class="fairy-text-link" href="#companionship">探索客服特色 <span aria-hidden="true">↓</span></a></div></div>
        <span class="fairy-greeting">你好呀，我是玲玲<span aria-hidden="true" /></span>
      </section>
    </div>

    <div class="fairy-features fairy-wrap">
      <section id="companionship" class="fairy-companion fairy-section" aria-labelledby="companion-title">
        <div class="fairy-feature-copy"><h2 id="companion-title">梦幻陪伴</h2><p class="fairy-feature-subtitle">温柔回应，随时为你解答</p><p>把每一次提问，变成轻松的交流。</p><FairyArtwork kind="horse" class="fairy-companion-horse" /></div>
        <div class="fairy-chat">
          <div class="fairy-chat-header"><FairyArtwork kind="avatar" class="fairy-avatar" /><h3>与玲玲聊聊</h3><span>互动演示</span></div>
          <div ref="conversation" class="fairy-chat-messages" role="log" aria-label="示例对话" aria-live="polite" aria-relevant="additions" tabindex="0">
            <div v-for="message in messages" :key="message.id" class="fairy-message" :class="`fairy-message--${message.role}`"><FairyArtwork v-if="message.role === 'assistant'" kind="avatar" class="fairy-avatar" /><p><span class="fairy-sr-only">{{ message.role === 'user' ? '你：' : '玲玲演示：' }}</span>{{ message.text }}</p><span v-if="message.role === 'user'" class="fairy-user-avatar" aria-hidden="true"><svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="8" r="4" /><path d="M4 22v-3a8 8 0 0 1 16 0v3Z" /></svg></span></div>
          </div>
          <form class="fairy-chat-form" @submit.prevent="ask(input)"><label for="fairy-question" class="fairy-sr-only">输入你想了解的问题</label><input id="fairy-question" ref="inputElement" v-model="input" type="text" autocomplete="off" maxlength="300" placeholder="输入你想了解的问题…" aria-describedby="fairy-demo-note" @keydown.enter="handleEnter" /><button type="submit" :disabled="!input.trim()" aria-label="发送问题"><FairyIcon name="send" /></button></form>
          <div class="fairy-chat-note"><span id="fairy-demo-note">示例互动，暂未连接实时客服</span><RouterLink to="/workspace">前往创作工作台 <span aria-hidden="true">↗</span></RouterLink></div>
        </div>
      </section>

      <section id="guidance" class="fairy-guidance fairy-section" aria-labelledby="guidance-title">
        <div class="fairy-route-art"><ol class="fairy-route-steps"><li><span><FairyIcon name="chat" /></span>说出问题</li><li><span><FairyIcon name="send" /></span>找到方向</li><li><span><FairyIcon name="check" /></span>继续操作</li></ol><FairyArtwork kind="book" class="fairy-route-book" /><i class="fairy-spark fairy-route-spark" aria-hidden="true" /></div>
        <div class="fairy-feature-copy"><h2 id="guidance-title">智能引导</h2><p class="fairy-feature-subtitle">清晰路径，帮你快速找到答案</p><p>把复杂问题拆成清楚的小步骤。</p><button class="fairy-text-link" type="button" @click="askQuickQuestion('下一步怎么操作？')">跟随玲玲，轻松开始 <FairyIcon name="arrow" /></button></div>
      </section>

      <div class="fairy-feature-pair">
        <section id="interface" class="fairy-interface fairy-section" aria-labelledby="interface-title"><h2 id="interface-title">童话界面</h2><p class="fairy-feature-subtitle">轻量交互，每一步都有惊喜</p><div class="fairy-quick-questions"><button v-for="question in questions" :key="question.text" type="button" @click="askQuickQuestion(question.text)"><span class="fairy-question-icon"><FairyIcon :name="question.icon" /></span>{{ question.text }}<FairyIcon name="arrow" class="fairy-question-arrow" /></button><i class="fairy-spark fairy-questions-spark" aria-hidden="true" /><span class="fairy-bubble" aria-hidden="true" /></div></section>
        <section id="memory" class="fairy-memory fairy-section" aria-labelledby="memory-title"><h2 id="memory-title">专属记忆</h2><p class="fairy-feature-subtitle">记住你的偏好，提供更贴心的服务</p><div class="fairy-memory-art"><FairyArtwork kind="book" class="fairy-memory-book" /><ul><li><FairyIcon name="heart" />你的偏好</li><li><FairyIcon name="feather" />熟悉的表达</li><li><FairyIcon name="chat" />连贯的对话</li></ul></div></section>
      </div>
    </div>

    <section class="fairy-closing" aria-labelledby="closing-title"><div class="fairy-closing-inner fairy-wrap"><FairyArtwork kind="portrait" class="fairy-closing-girl" /><div class="fairy-closing-copy"><h2 id="closing-title">开启童话般智能服务</h2><p>让每一次相遇，都多一点温暖。</p><button class="fairy-button" type="button" @click="focusConversation">开始对话</button></div><FairyArtwork kind="horse" class="fairy-closing-horse" /></div></section>
    <footer class="fairy-footer fairy-wrap"><span>玲玲 AI 客服 <span aria-hidden="true">·</span> 让智能服务像童话一样温暖</span><RouterLink to="/">返回平台首页 <span aria-hidden="true">↗</span></RouterLink></footer>
  </div>
</template>
