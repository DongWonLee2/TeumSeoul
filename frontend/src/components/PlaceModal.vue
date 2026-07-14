<script setup>
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { getCategoryMeta } from '../utils/category.js'

const props = defineProps({
  place: { type: Object, required: true },
})

const emit = defineEmits(['close'])
const meta = computed(() => getCategoryMeta(props.place.category))
const photoStyle = computed(() => ({
  backgroundImage: props.place.image_url
    ? `url(${props.place.image_url})`
    : `repeating-linear-gradient(45deg, ${meta.value.bg} 0 10px, ${meta.value.stripe} 10px 20px)`,
}))

function onKeydown(event) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => {
  document.body.classList.add('modal-open')
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.body.classList.remove('modal-open')
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="modal-backdrop" role="presentation" @click.self="$emit('close')">
    <article class="place-modal" role="dialog" aria-modal="true" :aria-label="`${place.title} 상세`">
      <div class="modal-head">
        <span>장소 상세</span>
        <button type="button" aria-label="닫기" @click="$emit('close')">✕</button>
      </div>
      <div class="modal-photo" :style="photoStyle">
        <span v-if="!place.image_url" :style="{ color: meta.fg }">PHOTO PLACEHOLDER</span>
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
      <h2>관련 게시글 ({{ place.related_post_count }})</h2>
      <div class="empty-related">
        {{ place.related_post_count ? '관련 게시글은 API 연결 후 표시됩니다.' : '아직 등록된 게시글이 없어요.' }}
      </div>
    </article>
  </div>
</template>
