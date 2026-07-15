<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import FilterChips from '../components/FilterChips.vue'
import LeafletMap from '../components/LeafletMap.vue'
import PlaceCard from '../components/PlaceCard.vue'
import { getLocations, getMapLocations } from '../api/locations.js'

defineProps({
  categories: { type: Array, required: true },
  districts: { type: Array, required: true },
})

const emit = defineEmits(['open-place', 'show-map'])
const searchQuery = ref('')
const activeCategory = ref('all')
const activeDistrict = ref('all')
const appliedSearchQuery = ref('')
const appliedCategory = ref('all')
const appliedDistrict = ref('all')
const places = ref([])
const totalItems = ref(0)
const listLoading = ref(false)
const listError = ref('')
const mapPlaces = ref([])
const mapMeta = ref({ count: 0, limit: 300, truncated: false })
const mapBounds = ref(null)
const mapLoading = ref(false)
const mapError = ref('')
let listController
let mapController

const visibleMapPlaces = computed(() => {
  const query = appliedSearchQuery.value.trim().toLowerCase()
  return mapPlaces.value.filter((place) => {
    const districtMatches = appliedDistrict.value === 'all' || place.district === appliedDistrict.value
    const queryMatches = !query
      || place.title.toLowerCase().includes(query)
      || (place.district || '').toLowerCase().includes(query)
    return districtMatches && queryMatches
  })
})

async function loadLocations() {
  listController?.abort()
  const currentController = new AbortController()
  listController = currentController
  listLoading.value = true
  listError.value = ''

  try {
    const response = await getLocations({
      q: appliedSearchQuery.value.trim(),
      content_type_id: appliedCategory.value,
      district: appliedDistrict.value,
      page: 1,
      size: 20,
      sort: 'recent',
    }, currentController.signal)
    if (listController !== currentController) return
    places.value = response.data
    totalItems.value = response.meta?.total_items ?? response.data.length
  } catch (error) {
    if (error.name === 'AbortError' || listController !== currentController) return
    places.value = []
    totalItems.value = 0
    listError.value = error.message || '장소 목록을 불러오지 못했습니다.'
  } finally {
    if (listController === currentController) listLoading.value = false
  }
}

async function loadMapPlaces() {
  if (!mapBounds.value) return
  mapController?.abort()
  const currentController = new AbortController()
  mapController = currentController
  mapLoading.value = true
  mapError.value = ''

  try {
    const response = await getMapLocations({
      ...mapBounds.value,
      content_type_ids: appliedCategory.value === 'all' ? undefined : appliedCategory.value,
      limit: 300,
    }, currentController.signal)
    if (mapController !== currentController) return
    mapPlaces.value = response.data
    mapMeta.value = response.meta
  } catch (error) {
    if (error.name === 'AbortError' || mapController !== currentController) return
    mapPlaces.value = []
    mapError.value = error.message || '지도 장소를 불러오지 못했습니다.'
  } finally {
    if (mapController === currentController) mapLoading.value = false
  }
}

function onBoundsChange(bounds) {
  mapBounds.value = bounds
  loadMapPlaces()
}

function applyFilters() {
  appliedSearchQuery.value = searchQuery.value
  appliedCategory.value = activeCategory.value
  appliedDistrict.value = activeDistrict.value
  loadLocations()
  loadMapPlaces()
}

onMounted(loadLocations)

onBeforeUnmount(() => {
  listController?.abort()
  mapController?.abort()
})
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

  <main class="home-layout">
    <section class="place-preview">
      <div class="section-summary">
        <span>전체 {{ totalItems.toLocaleString() }}곳 중 일부</span>
        <button type="button" @click="$emit('show-map')">전체보기 ›</button>
      </div>

      <div v-if="listLoading" class="content-status" role="status">장소를 불러오는 중…</div>
      <div v-else-if="listError" class="content-status error" role="alert">
        <span>{{ listError }}</span>
        <button type="button" @click="loadLocations">다시 시도</button>
      </div>
      <div v-else-if="places.length" class="place-list">
        <PlaceCard
          v-for="place in places.slice(0, 4)"
          :key="place.id"
          :place="place"
          @open="$emit('open-place', $event)"
        />
      </div>
      <div v-else class="empty-results">
        <strong>검색 결과가 없어요</strong>
        <span>다른 키워드나 카테고리로 찾아보세요</span>
      </div>
    </section>

    <section class="map-section">
      <p v-if="mapMeta.truncated" class="map-notice">
        현재 영역에 장소가 많아 일부만 표시됩니다. 지도를 확대해 주세요.
      </p>
      <p v-if="mapError" class="map-notice error" role="alert">{{ mapError }}</p>
      <LeafletMap
        :places="visibleMapPlaces"
        :categories="categories"
        :loading="mapLoading"
        @bounds-change="onBoundsChange"
        @open-place="emit('open-place', $event)"
      />
    </section>
  </main>
</template>
