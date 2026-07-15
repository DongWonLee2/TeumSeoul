<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import FilterChips from '../components/FilterChips.vue'
import LeafletMap from '../components/LeafletMap.vue'
import PlaceCard from '../components/PlaceCard.vue'
import { getLocations, getMapLocations } from '../api/locations.js'

defineProps({
  categories: { type: Array, required: true },
  districts: { type: Array, required: true },
})

const emit = defineEmits(['open-place'])

const searchQuery = ref('')
const activeCategory = ref('all')
const activeDistrict = ref('all')
const appliedSearchQuery = ref('')
const appliedCategory = ref('all')
const appliedDistrict = ref('all')
const places = ref([])
const mapMeta = ref({ count: 0, limit: 300, truncated: false })
const mapBounds = ref(null)
const loading = ref(false)
const error = ref('')
const fitRequest = ref(0)
const focusedPlace = ref(null)
const focusRequest = ref(0)
let controller

const visiblePlaces = computed(() => {
  const query = appliedSearchQuery.value.trim().toLowerCase()
  return places.value.filter((place) => {
    const districtMatches = appliedDistrict.value === 'all' || place.district === appliedDistrict.value
    const queryMatches = !query
      || place.title.toLowerCase().includes(query)
      || (place.district || '').toLowerCase().includes(query)
    return districtMatches && queryMatches
  })
})

async function loadMapPlaces() {
  if (!mapBounds.value) return
  controller?.abort()
  const currentController = new AbortController()
  controller = currentController
  loading.value = true
  error.value = ''

  try {
    const useLocationSearch = Boolean(appliedSearchQuery.value.trim())
      || appliedDistrict.value !== 'all'
    const response = useLocationSearch
      ? await getLocations({
          q: appliedSearchQuery.value.trim(),
          content_type_id: appliedCategory.value,
          district: appliedDistrict.value,
          page: 1,
          size: 100,
          sort: 'recent',
        }, currentController.signal)
      : await getMapLocations({
          ...mapBounds.value,
          content_type_ids: appliedCategory.value === 'all' ? undefined : appliedCategory.value,
          limit: 300,
        }, currentController.signal)
    if (controller !== currentController) return
    places.value = response.data
    mapMeta.value = useLocationSearch
      ? {
          count: response.data.length,
          limit: response.meta?.size ?? 100,
          truncated: (response.meta?.total_items ?? response.data.length) > response.data.length,
        }
      : response.meta
  } catch (requestError) {
    if (requestError.name === 'AbortError' || controller !== currentController) return
    places.value = []
    error.value = requestError.message || '지도 장소를 불러오지 못했습니다.'
  } finally {
    if (controller === currentController) loading.value = false
  }
}

function onBoundsChange(bounds) {
  mapBounds.value = bounds
  if (appliedSearchQuery.value.trim() || appliedDistrict.value !== 'all') return
  loadMapPlaces()
}

async function applyFilters() {
  appliedSearchQuery.value = searchQuery.value
  appliedCategory.value = activeCategory.value
  appliedDistrict.value = activeDistrict.value
  await loadMapPlaces()
  if (places.value.length) fitRequest.value += 1
}

function selectPlace(place) {
  focusedPlace.value = place
  focusRequest.value += 1
  emit('open-place', place)
}

onBeforeUnmount(() => controller?.abort())
</script>

<template>
  <FilterChips
    v-model:search-query="searchQuery"
    :categories="categories"
    :districts="districts"
    :active-category="activeCategory"
    :active-district="activeDistrict"
    @select-category="activeCategory = $event"
    @select-district="activeDistrict = $event"
    @search="applyFilters"
  />

  <main class="map-page">
    <div class="map-title">
      <h1>지도</h1>
      <span>현재 영역 {{ visiblePlaces.length.toLocaleString() }}곳</span>
    </div>

    <p v-if="mapMeta.truncated" class="map-notice">
      현재 영역에 장소가 많아 최대 {{ mapMeta.limit }}곳만 표시됩니다. 지도를 확대해 주세요.
    </p>
    <p v-if="error" class="map-notice error" role="alert">
      {{ error }}
      <button type="button" @click="loadMapPlaces">다시 시도</button>
    </p>

    <LeafletMap
      :places="visiblePlaces"
      :categories="categories"
      :loading="loading"
      :fit-request="fitRequest"
      :focus-place="focusedPlace"
      :focus-request="focusRequest"
      height="min(640px, 70vh)"
      @bounds-change="onBoundsChange"
      @open-place="selectPlace"
    />

    <div v-if="visiblePlaces.length" class="map-card-row">
      <PlaceCard
        v-for="place in visiblePlaces.slice(0, 20)"
        :key="place.id"
        :place="place"
        compact
        @open="selectPlace"
      />
    </div>
    <div v-else-if="!loading && !error" class="empty-results map-empty">
      <strong>검색 결과가 없어요</strong>
      <span>필터를 바꾸거나 지도를 이동해 보세요.</span>
    </div>
  </main>
</template>
