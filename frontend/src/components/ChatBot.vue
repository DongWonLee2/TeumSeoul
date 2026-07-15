<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { placeDetailRouteName } from '../router/index.js'
import { sendChatMessage } from '../api/chat.js'
import { getPostDetail } from '../api/posts.js'
import { formatPostTime } from '../utils/datetime.js'

const route = useRoute()
const router = useRouter()

const chatOpen = ref(false)
const chatPanel = ref(null)
const panelWidth = ref(null)
const panelHeight = ref(null)
const panelStyle = computed(() => (
  panelWidth.value && panelHeight.value
    ? { width: `${panelWidth.value}px`, height: `${panelHeight.value}px` }
    : {}
))
const PANEL_BASE_WIDTH = 380
const PANEL_SCALE_GROWTH = 200
const PANEL_MAX_SCALE = 1.18
const cardScale = computed(() => {
  const width = panelWidth.value || PANEL_BASE_WIDTH
  const ratio = Math.min(1, Math.max(0, (width - PANEL_BASE_WIDTH) / PANEL_SCALE_GROWTH))
  return 1 + ratio * (PANEL_MAX_SCALE - 1)
})
const panelVars = computed(() => ({ '--card-scale': cardScale.value }))
let dragStart = null
const messages = ref([
  {
    isAi: true,
    text: '안녕하세요! 서울 곳곳을 더 쉽게 찾아드릴게요. 궁금한 장소나 분위기를 말씀해 주세요.',
  },
])
const chatInput = ref('')
const chatBusy = ref(false)
const chatError = ref('')

function toggleChat() {
  chatOpen.value = !chatOpen.value
  if (!chatOpen.value) chatError.value = ''
}

function startResize(event) {
  const rect = chatPanel.value.getBoundingClientRect()
  dragStart = { x: event.clientX, y: event.clientY, width: rect.width, height: rect.height }
  window.addEventListener('pointermove', onResizeMove)
  window.addEventListener('pointerup', stopResize)
  event.preventDefault()
}

function onResizeMove(event) {
  if (!dragStart) return
  const minWidth = Math.min(380, window.innerWidth - 32)
  const minHeight = Math.min(560, window.innerHeight - 140)
  const maxWidth = window.innerWidth - 32
  const maxHeight = window.innerHeight - 140
  panelWidth.value = Math.min(maxWidth, Math.max(minWidth, dragStart.width + (dragStart.x - event.clientX)))
  panelHeight.value = Math.min(maxHeight, Math.max(minHeight, dragStart.height + (dragStart.y - event.clientY)))
}

function stopResize() {
  dragStart = null
  window.removeEventListener('pointermove', onResizeMove)
  window.removeEventListener('pointerup', stopResize)
}

onBeforeUnmount(stopResize)

function onChatKeyDown(event) {
  if (event.key === 'Enter') {
    event.preventDefault()
    sendChatInput()
  }
}

function getCurrentLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
      () => resolve(null),
      { timeout: 3000 },
    )
  })
}

async function sendChatInput() {
  const message = chatInput.value.trim()
  if (!message || chatBusy.value) return

  chatBusy.value = true
  chatError.value = ''
  messages.value.push({ isUser: true, text: message })
  chatInput.value = ''

  const history = messages.value
    .slice(-8)
    .filter((entry) => entry.isUser || entry.isAi)
    .map((entry) => ({ role: entry.isUser ? 'user' : 'assistant', content: entry.text }))

  try {
    const location = await getCurrentLocation()
    const payload = {
      message,
      context: location ? { current_location: location } : undefined,
      history,
    }
    const response = await sendChatMessage(payload)
    const data = response?.answer || '추천 결과를 불러오지 못했습니다.'
    const resultCards = (response?.results || []).slice(0, 3).map((item) => ({
      name: item.title,
      catLabel: item.content_type || '장소',
      catBg: 'oklch(95% 0.02 190)',
      catFg: 'var(--accent-2)',
      ground: item.address || '정보 확인 필요',
      postCount: (response?.community_posts || []).filter((post) => post.location_id === item.location_id).length,
      onClick: () => router.push({
        name: placeDetailRouteName(route.meta.section || 'home'),
        params: { id: item.location_id },
      }),
    }))
    const rawPosts = (response?.community_posts || []).slice(0, 3)
    const postDetails = await Promise.all(
      rawPosts.map((post) => getPostDetail(post.post_id).catch(() => null)),
    )
    const postCards = rawPosts.map((post, index) => ({
      title: post.title,
      placeName: postDetails[index]?.location?.title || '장소 미정',
      time: formatPostTime(postDetails[index]?.created_at),
      onClick: () => router.push({ name: 'community', query: { post: post.post_id } }),
    }))

    messages.value.push({
      isAi: true,
      text: data,
      hasCards: resultCards.length > 0,
      cardList: resultCards,
      hasPosts: postCards.length > 0,
      postList: postCards,
    })
  } catch (error) {
    chatError.value = error?.message || '챗봇 요청에 실패했습니다.'
    messages.value.push({
      isAi: true,
      text: '현재는 추천 결과를 불러오지 못해, 주변 장소와 커뮤니티 글로 대체해 안내해드릴게요.',
    })
  } finally {
    chatBusy.value = false
  }
}
</script>

<template>
  <div>
    <button class="chat-toggle" type="button" @click="toggleChat" aria-label="AI 챗봇 열기">💬</button>

    <div v-if="chatOpen" ref="chatPanel" class="chat-panel" role="dialog" aria-label="AI 챗봇" :style="[panelStyle, panelVars]">
      <div class="chat-resize-handle" aria-hidden="true" @pointerdown="startResize" />
      <div class="chat-header">
        <div class="chat-title">TeumSeoul AI</div>
        <button class="chat-close" type="button" @click="toggleChat" aria-label="AI 챗봇 닫기">✕</button>
      </div>

      <div class="chat-body">
        <div v-for="(message, index) in messages" :key="index" class="chat-message-row">
          <div v-if="message.isUser" class="chat-bubble chat-bubble-user">{{ message.text }}</div>
          <template v-else>
            <div class="chat-bubble chat-bubble-ai">{{ message.text }}</div>

            <div v-if="message.hasCards" class="chat-cards">
              <button
                v-for="(card, cardIndex) in message.cardList"
                :key="cardIndex"
                type="button"
                class="chat-card"
                @click="card.onClick"
              >
                <div class="chat-card-head">
                  <span class="chat-card-cat" :style="{ background: card.catBg, color: card.catFg }">{{ card.catLabel }}</span>
                  <span class="chat-card-name">{{ card.name }}</span>
                </div>
                <div class="chat-card-meta">📊 데이터 근거 · {{ card.ground }}</div>
                <div class="chat-card-meta">📝 관련 게시글 · {{ card.postCount }}건</div>
              </button>
            </div>

            <div v-if="message.hasPosts" class="chat-cards">
              <div class="chat-section-label">📝 관련 커뮤니티 글</div>
              <button
                v-for="(post, postIndex) in message.postList"
                :key="postIndex"
                type="button"
                class="chat-card"
                @click="post.onClick"
              >
                <div class="chat-card-meta-line">
                  <span class="chat-card-name">{{ post.title }}</span>
                  <span class="chat-card-meta">📍 {{ post.placeName }} · {{ post.time }}</span>
                </div>
              </button>
            </div>
          </template>
        </div>

        <div v-if="chatBusy" class="chat-message-row">
          <div class="chat-bubble chat-bubble-ai chat-typing">
            <span class="chat-typing-dot" /><span class="chat-typing-dot" /><span class="chat-typing-dot" />
          </div>
        </div>

        <div v-if="chatError" class="chat-error">{{ chatError }}</div>
      </div>

      <div class="chat-input-row">
        <input
          v-model="chatInput"
          type="text"
          placeholder="궁금한 걸 물어보세요"
          @keydown="onChatKeyDown"
        />
        <button type="button" class="chat-send" @click="sendChatInput">➤</button>
      </div>
    </div>
  </div>
</template>
