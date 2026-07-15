<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import FilterChips from '../components/FilterChips.vue'
import LeafletMap from '../components/LeafletMap.vue'
import PlaceCard from '../components/PlaceCard.vue'
import SituationalRecommendationPanel from '../components/SituationalRecommendationPanel.vue'
import { getLocationDetail, getLocations, getMapLocations } from '../api/locations.js'

const props = defineProps({
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
const selectedCourse = ref(null)
const coursePlaces = ref([])
const courseLoading = ref(false)
const courseError = ref('')
let controller
let courseController

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

const displayedPlaces = computed(() => selectedCourse.value ? coursePlaces.value : visiblePlaces.value)

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
  if (selectedCourse.value) return
  if (appliedSearchQuery.value.trim() || appliedDistrict.value !== 'all') return
  loadMapPlaces()
}

async function applyFilters() {
  clearSelectedCourse(false)
  appliedSearchQuery.value = searchQuery.value
  appliedCategory.value = activeCategory.value
  appliedDistrict.value = activeDistrict.value
  await loadMapPlaces()
  if (places.value.length) fitRequest.value += 1
}

function selectPlace(place) {
  emit('open-place', place)
}

async function selectCourse(course) {
  controller?.abort()
  courseController?.abort()
  const currentController = new AbortController()
  courseController = currentController
  selectedCourse.value = course
  coursePlaces.value = []
  courseLoading.value = true
  courseError.value = ''

  const locations = course.locations || []
  const results = await Promise.allSettled(
    locations.map((location) => getLocationDetail(location.id, currentController.signal)),
  )
  if (courseController !== currentController) return

  coursePlaces.value = results.flatMap((result, index) => {
    if (result.status !== 'fulfilled') return []
    const recommendationPlace = locations[index]
    return [{
      ...recommendationPlace,
      ...result.value,
      image_url: result.value.image_url || recommendationPlace.image_url,
      courseOrder: index + 1,
    }]
  })
  const failedCount = results.length - coursePlaces.value.length
  if (failedCount) courseError.value = `${failedCount}개 장소의 위치를 지도에 표시하지 못했어요.`
  courseLoading.value = false
  if (coursePlaces.value.length) fitRequest.value += 1
}

function clearSelectedCourse(reload = true) {
  courseController?.abort()
  courseController = null
  selectedCourse.value = null
  coursePlaces.value = []
  courseLoading.value = false
  courseError.value = ''
  if (reload && mapBounds.value) loadMapPlaces()
}

function openRecommendedPlace(place) {
  const detailedPlace = coursePlaces.value.find((item) => String(item.id) === String(place.id))
  selectPlace(detailedPlace || place)
}

function focusSelectedPlace(place) {
  focusedPlace.value = place
  focusRequest.value += 1
}

defineExpose({ focusSelectedPlace })

onBeforeUnmount(() => {
  controller?.abort()
  courseController?.abort()
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

  <main class="map-page recommendation-map-page">
    <section class="map-section">
    <div class="map-title">
      <h1>지도</h1>
      <span>{{ selectedCourse ? '선택 코스' : '현재 영역' }} {{ displayedPlaces.length.toLocaleString() }}곳</span>
    </div>

    <p v-if="mapMeta.truncated && !selectedCourse" class="map-notice">
      현재 영역에 장소가 많아 최대 {{ mapMeta.limit }}곳만 표시됩니다. 지도를 확대해 주세요.
    </p>
    <p v-if="error" class="map-notice error" role="alert">
      {{ error }}
      <button type="button" @click="loadMapPlaces">다시 시도</button>
    </p>
    <p v-if="courseError" class="map-notice error" role="alert">{{ courseError }}</p>

    <LeafletMap
      :places="displayedPlaces"
      :categories="categories"
      :loading="loading || courseLoading"
      :fit-request="fitRequest"
      :focus-place="focusedPlace"
      :focus-request="focusRequest"
      height="min(640px, 70vh)"
      @bounds-change="onBoundsChange"
      @open-place="selectPlace"
    />

    <div v-if="displayedPlaces.length" class="map-card-row">
      <PlaceCard
        v-for="place in displayedPlaces.slice(0, 20)"
        :key="place.id"
        :place="place"
        compact
        @open="selectPlace"
      />
    </div>
    <div v-else-if="!loading && !courseLoading && !error" class="empty-results map-empty">
      <strong>검색 결과가 없어요</strong>
      <span>필터를 바꾸거나 지도를 이동해 보세요.</span>
    </div>
    </section>

    <SituationalRecommendationPanel
      :districts="props.districts"
      :selected-course-id="selectedCourse?.id"
      @select-course="selectCourse"
      @clear-course="clearSelectedCourse"
      @open-place="openRecommendedPlace"
    />
  </main>
</template>
