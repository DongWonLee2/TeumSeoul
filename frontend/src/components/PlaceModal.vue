<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getCategoryMeta } from '../utils/category.js'

const props = defineProps({
  place: { type: Object, required: true },
})

const emit = defineEmits(['close'])
const copyStatus = ref('idle')
let copyStatusTimer
const meta = computed(() => getCategoryMeta(props.place.content_type_id))
const currentImage = computed(() => props.place.image_url)
const visibleWarnings = computed(() =>
  (props.place.warnings ?? []).filter((warning) => !warning.includes('대표 이미지 없음')),
)
const photoStyle = computed(() => ({
  backgroundImage: currentImage.value
    ? `url(${currentImage.value})`
    : `repeating-linear-gradient(45deg, ${meta.value.bg} 0 10px, ${meta.value.stripe} 10px 20px)`,
}))

function fallbackCopy(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand('copy')
  textarea.remove()
  if (!copied) throw new Error('링크 복사에 실패했습니다.')
}

async function copyPlaceLink() {
  const placeUrl = new URL(`/places/${props.place.id}`, window.location.origin).href

  try {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(placeUrl)
    } else {
      fallbackCopy(placeUrl)
    }
    copyStatus.value = 'success'
  } catch {
    copyStatus.value = 'error'
  }

  window.clearTimeout(copyStatusTimer)
  copyStatusTimer = window.setTimeout(() => {
    copyStatus.value = 'idle'
  }, 2000)
}

function onKeydown(event) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => {
  document.body.classList.add('modal-open')
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.clearTimeout(copyStatusTimer)
  document.body.classList.remove('modal-open')
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="modal-backdrop" role="presentation" @click.self="$emit('close')">
    <article class="place-modal" role="dialog" aria-modal="true" :aria-label="`${place.title} 상세`">
      <div class="modal-head">
        <span>장소 상세</span>
        <div class="modal-actions">
          <button
            type="button"
            class="share-link-button"
            :class="{ copied: copyStatus === 'success' }"
            @click="copyPlaceLink"
          >
            {{ copyStatus === 'success' ? '✓ 복사됨' : '🔗 링크 복사' }}
          </button>
          <button type="button" class="modal-close" aria-label="닫기" @click="$emit('close')">✕</button>
        </div>
      </div>
      <p v-if="copyStatus === 'error'" class="copy-error" role="alert">
        링크를 복사하지 못했습니다. 주소창의 URL을 복사해 주세요.
      </p>
      <span class="sr-only" aria-live="polite">
        {{ copyStatus === 'success' ? '장소 링크가 클립보드에 복사되었습니다.' : '' }}
      </span>
      <div class="modal-photo" :style="photoStyle">
        <span v-if="!currentImage" :style="{ color: meta.fg }">PHOTO PLACEHOLDER</span>
      </div>
      <div class="modal-badges">
        <span class="category-badge" :style="{ background: meta.bg, color: meta.fg }">
          {{ place.content_type }}
        </span>
        <span>{{ place.district }}</span>
      </div>
      <h1>{{ place.title }}</h1>
      <div class="place-details">
        <span>📍 {{ place.address || '주소 정보 없음' }}</span>
        <span>📞 {{ place.telephone || '전화번호 정보 없음' }}</span>
        <span>🔄 갱신일 {{ place.source_modified_at?.slice(0, 10) }}</span>
      </div>
      <div class="data-source">📊 데이터 근거 · {{ meta.source }}</div>
      <div v-if="visibleWarnings.length" class="place-warnings">
        <strong>방문 전 확인해 주세요</strong>
        <ul>
          <li v-for="warning in visibleWarnings" :key="warning">{{ warning }}</li>
        </ul>
      </div>
      <h2>관련 게시글 ({{ place.related_post_count ?? 0 }})</h2>
      <div class="empty-related">
        {{ place.related_post_count ? '관련 게시글은 API 연결 후 표시됩니다.' : '아직 등록된 게시글이 없어요.' }}
      </div>
    </article>
  </div>
</template>
