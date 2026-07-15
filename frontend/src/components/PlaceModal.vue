<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getCategoryMeta } from '../utils/category.js'

const props = defineProps({
  place: { type: Object, required: true },
})

const emit = defineEmits(['close'])
const currentImageIndex = ref(0)
const meta = computed(() => getCategoryMeta(props.place.content_type_id))
const images = computed(() => [
  props.place.thumbnail_url,
  props.place.image_url,
].filter((url, index, items) => url && items.indexOf(url) === index))
const currentImage = computed(() => images.value[currentImageIndex.value])
const photoStyle = computed(() => ({
  backgroundImage: currentImage.value
    ? `url(${currentImage.value})`
    : `repeating-linear-gradient(45deg, ${meta.value.bg} 0 10px, ${meta.value.stripe} 10px 20px)`,
}))

function showPreviousImage() {
  currentImageIndex.value = (currentImageIndex.value - 1 + images.value.length) % images.value.length
}

function showNextImage() {
  currentImageIndex.value = (currentImageIndex.value + 1) % images.value.length
}

function onKeydown(event) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => {
  document.body.classList.add('modal-open')
  window.addEventListener('keydown', onKeydown)
})

watch(() => props.place.id, () => {
  currentImageIndex.value = 0
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
        <span v-if="!images.length" :style="{ color: meta.fg }">PHOTO PLACEHOLDER</span>
        <template v-else-if="images.length > 1">
          <button
            type="button"
            class="photo-nav previous"
            aria-label="이전 사진"
            @click="showPreviousImage"
          >
            ‹
          </button>
          <span class="photo-position">{{ currentImageIndex + 1 }} / {{ images.length }}</span>
          <button
            type="button"
            class="photo-nav next"
            aria-label="다음 사진"
            @click="showNextImage"
          >
            ›
          </button>
        </template>
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
      <h2>관련 게시글 ({{ place.related_post_count ?? 0 }})</h2>
      <div class="empty-related">
        {{ place.related_post_count ? '관련 게시글은 API 연결 후 표시됩니다.' : '아직 등록된 게시글이 없어요.' }}
      </div>
    </article>
  </div>
</template>
