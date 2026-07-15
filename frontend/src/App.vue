<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import AppHeader from './components/AppHeader.vue'
import PlaceModal from './components/PlaceModal.vue'

import { getLocationDetail } from './api/locations.js'
import { getHealth, getMeta } from './api/system.js'

import { CATEGORIES, PLACES, SEOUL_DISTRICTS } from './data/places.js'

const route = useRoute()
const router = useRouter()
const categories = ref(CATEGORIES)
const districts = ref(SEOUL_DISTRICTS)
const health = ref(null)
const systemError = ref('')
const selectedPlace = ref(null)
const placeLoading = ref(false)
const placeError = ref('')
const activeView = ref(null)
let detailRequestId = 0

const currentView = computed(() => route.meta.section || 'home')
const isPlaceRoute = computed(() => Boolean(route.meta.placeModal && route.params.id))

function navigate(view) {
  const routeNames = { home: 'home', map: 'map', community: 'community' }
  router.push({ name: routeNames[view] || 'home' })
}

function openPlace(place) {
  if (currentView.value === 'map') activeView.value?.focusSelectedPlace?.(place)
  const routeName = currentView.value === 'map' ? 'map-place-detail' : 'place-detail'
  router.push({ name: routeName, params: { id: place.id } })
}

function closePlace() {
  router.push({ name: currentView.value === 'map' ? 'map' : 'home' })
}

function openPost(post) {
  router.push({ name: 'community', query: { post: post.id } })
}

async function loadPlaceDetail(id) {
  const requestId = ++detailRequestId
  selectedPlace.value = null
  placeError.value = ''
  placeLoading.value = true

  try {
    const detail = await getLocationDetail(id)
    if (requestId === detailRequestId) selectedPlace.value = detail
  } catch (error) {
    const sample = PLACES.find((place) => String(place.id) === String(id))
    if (requestId !== detailRequestId) return
    if (sample) selectedPlace.value = sample
    else placeError.value = error.message || '장소 정보를 불러오지 못했습니다.'
  } finally {
    if (requestId === detailRequestId) placeLoading.value = false
  }
}

watch(
  () => route.params.id,
  (id) => {
    if (isPlaceRoute.value) loadPlaceDetail(id)
    else {
      detailRequestId += 1
      selectedPlace.value = null
      placeError.value = ''
      placeLoading.value = false
    }
  },
  { immediate: true },
)

onMounted(async () => {
  const [healthResult, metaResult] = await Promise.allSettled([getHealth(), getMeta()])

  if (healthResult.status === 'fulfilled') health.value = healthResult.value
  else systemError.value = '백엔드 서버에 연결할 수 없어 일부 기능이 제한됩니다.'

  if (metaResult.status === 'fulfilled') {
    categories.value = metaResult.value.content_types || CATEGORIES
    districts.value = metaResult.value.districts || SEOUL_DISTRICTS
  }
})
</script>

<template>
  <div class="app-shell" :data-server-status="health?.status || 'offline'">
    <AppHeader :current-view="currentView" @navigate="navigate" />

    <div v-if="systemError" class="connection-alert" role="status">
      {{ systemError }}
    </div>

    <RouterView v-slot="{ Component }">
      <component
        ref="activeView"
        :is="Component"
        :categories="categories"
        :districts="districts"
        @open-place="openPlace"
        @show-map="navigate('map')"
      />
    </RouterView>

    <div v-if="isPlaceRoute && placeLoading" class="modal-backdrop place-loading" role="status">
      장소 정보를 불러오는 중입니다…
    </div>
    <div v-else-if="isPlaceRoute && placeError" class="modal-backdrop" @click.self="closePlace">
      <div class="place-load-error" role="alert">
        <strong>{{ placeError }}</strong>
        <button type="button" @click="closePlace">닫기</button>
      </div>
    </div>
    <PlaceModal
      v-else-if="isPlaceRoute && selectedPlace"
      :place="selectedPlace"
      @close="closePlace"
      @open-place="openPlace"
      @open-post="openPost"
    />
  </div>
</template>
