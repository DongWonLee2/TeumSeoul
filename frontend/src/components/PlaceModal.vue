<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getLocationDetail } from '../api/locations.js'
import { CATEGORIES } from '../data/places.js'
import { getCategoryMeta } from '../utils/category.js'

const props = defineProps({
  place: { type: Object, required: true },
})

const emit = defineEmits(['close', 'open-place', 'open-post'])
const copyStatus = ref('idle')
const nearbyPlaces = ref([])
const nearbyLoading = ref(false)
const nearbyError = ref('')
let copyStatusTimer
let nearbyController
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

function nearbyMeta(place) {
  const category = CATEGORIES.find((item) => item.name === place.content_type)
  return getCategoryMeta(place.content_type_id ?? category?.id)
}

function nearbyPhotoStyle(place) {
  const category = nearbyMeta(place)
  const imageUrl = place.thumbnail_url || place.image_url
  return {
    backgroundImage: imageUrl
      ? `url(${imageUrl})`
      : `repeating-linear-gradient(45deg, ${category.bg} 0 8px, ${category.stripe} 8px 16px)`,
  }
}

function distanceLabel(distanceKm) {
  if (!Number.isFinite(distanceKm)) return '거리 정보 없음'
  return distanceKm < 1
    ? `${Math.round(distanceKm * 1000).toLocaleString()}m`
    : `${distanceKm.toFixed(1)}km`
}

function walkingTime(distanceKm) {
  if (!Number.isFinite(distanceKm)) return ''
  return `도보 ${Math.max(1, Math.round(distanceKm * 12.5))}분`
}

function relatedPostDate(createdAt) {
  if (!createdAt) return ''
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(createdAt))
}

async function loadNearbyPlaces() {
  nearbyController?.abort()
  const sourcePlaces = (props.place.nearby_locations ?? []).slice(0, 4)
  nearbyPlaces.value = sourcePlaces
  nearbyError.value = ''
  if (!sourcePlaces.length) return

  const currentController = new AbortController()
  nearbyController = currentController
  nearbyLoading.value = true

  try {
    const results = await Promise.allSettled(
      sourcePlaces.map((place) => getLocationDetail(place.id, currentController.signal)),
    )
    if (nearbyController !== currentController) return
    nearbyPlaces.value = sourcePlaces.map((place, index) => (
      results[index].status === 'fulfilled'
        ? { ...place, ...results[index].value, distance_km: place.distance_km }
        : place
    ))
  } catch (error) {
    if (error.name !== 'AbortError') nearbyError.value = '근처 장소의 이미지를 불러오지 못했습니다.'
  } finally {
    if (nearbyController === currentController) nearbyLoading.value = false
  }
}

function openNearbyPlace(place) {
  emit('open-place', place)
}

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

watch(() => props.place.id, loadNearbyPlaces, { immediate: true })

onBeforeUnmount(() => {
  window.clearTimeout(copyStatusTimer)
  nearbyController?.abort()
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
      <section class="related-section" aria-labelledby="related-title">
        <h2 id="related-title">관련 게시글 ({{ place.related_post_count ?? 0 }})</h2>
        <div v-if="place.related_posts?.length" class="related-post-list">
          <button
            v-for="post in place.related_posts"
            :key="post.id"
            type="button"
            class="related-post-card"
            :aria-label="`${post.title} 게시글 보기`"
            @click="$emit('open-post', post)"
          >
            <span class="related-post-main">
              <span class="related-post-heading">
                <span class="related-post-category">{{ post.category }}</span>
                <strong>{{ post.title }}</strong>
              </span>
              <span class="related-post-meta">
                <span v-if="post.status_tag" class="related-post-status">{{ post.status_tag }}</span>
                <span>{{ relatedPostDate(post.created_at) }}</span>
              </span>
            </span>
            <span class="related-post-chevron" aria-hidden="true">›</span>
          </button>
        </div>
        <div v-else class="empty-related">아직 등록된 게시글이 없어요.</div>
      </section>
      <section class="nearby-section" aria-labelledby="nearby-title">
        <div class="nearby-heading">
          <h2 id="nearby-title">근처 장소</h2>
          <span>반경 1km</span>
        </div>
        <p v-if="nearbyError" class="nearby-error" role="status">{{ nearbyError }}</p>
        <div v-if="nearbyPlaces.length" class="nearby-grid" :aria-busy="nearbyLoading">
          <button
            v-for="nearby in nearbyPlaces"
            :key="nearby.id"
            type="button"
            class="nearby-card"
            :aria-label="`${nearby.title} 상세 보기`"
            @click="openNearbyPlace(nearby)"
          >
            <span class="nearby-photo" :style="nearbyPhotoStyle(nearby)">
              <span v-if="!nearby.thumbnail_url && !nearby.image_url">PHOTO</span>
            </span>
            <span class="nearby-info">
              <span
                class="category-badge"
                :style="{ background: nearbyMeta(nearby).bg, color: nearbyMeta(nearby).fg }"
              >
                {{ nearby.content_type }}
              </span>
              <span class="nearby-distance">
                {{ walkingTime(nearby.distance_km) }} · {{ distanceLabel(nearby.distance_km) }}
              </span>
              <strong>{{ nearby.title }}</strong>
            </span>
            <span class="nearby-chevron" aria-hidden="true">›</span>
          </button>
        </div>
        <div v-else class="nearby-empty">
          등록된 근처 장소가 없어요.
        </div>
      </section>
    </article>
  </div>
</template>
