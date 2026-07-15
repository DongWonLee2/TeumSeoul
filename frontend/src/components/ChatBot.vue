<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { placeDetailRouteName } from '../router/index.js'
import { sendChatMessage } from '../api/chat.js'

const route = useRoute()
const router = useRouter()

const chatOpen = ref(false)
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
      postText: (response?.community_posts || []).find((post) => post.location_id === item.location_id)?.title || '관련 커뮤니티 글 없음',
      onClick: () => router.push({
        name: placeDetailRouteName(route.meta.section || 'home'),
        params: { id: item.location_id },
      }),
    }))

    messages.value.push({
      isAi: true,
      text: data,
      hasCards: resultCards.length > 0,
      cardList: resultCards,
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

    <div v-if="chatOpen" class="chat-panel" role="dialog" aria-label="AI 챗봇">
      <div class="chat-header">
        <div class="chat-title">TeumSeoul AI</div>
        <button class="chat-close" type="button" @click="toggleChat" aria-label="AI 챗봇 닫기">✕</button>
      </div>

      <div class="chat-body">
        <div v-for="(message, index) in messages" :key="index" class="chat-message-row">
          <div v-if="message.isUser" class="chat-bubble chat-bubble-user">{{ message.text }}</div>
          <div v-else class="chat-bubble chat-bubble-ai">
            <div>{{ message.text }}</div>
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
                <div class="chat-card-meta">📝 최신 게시글 · {{ card.postText }}</div>
              </button>
            </div>
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
