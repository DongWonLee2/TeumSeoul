<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getSituationalRecommendations } from '../api/recommendations.js'
import { getCategoryMeta } from '../utils/category.js'

const props = defineProps({
  districts: { type: Array, required: true },
  selectedCourseId: { type: [String, Number], default: null },
})

const emit = defineEmits(['select-course', 'clear-course', 'open-place', 'results-change'])

const mode = ref('nearby')
const availableMinutes = ref(120)
const companion = ref('solo')
const mood = ref('healing')
const district = ref(props.districts[0] || '')
const currentLocation = ref(null)
const locationStatus = ref('idle')
const locationError = ref('')
const districtOpen = ref(false)
const districtDropdown = ref(null)
const loading = ref(false)
const error = ref('')
const result = ref(null)
let controller
const MAX_LOCATION_ACCURACY_METERS = 1000

const times = [
  { value: 30, label: '30분' },
  { value: 60, label: '1시간' },
  { value: 120, label: '2시간' },
  { value: 240, label: '4시간' },
]
const companions = [
  { value: 'solo', label: '혼자' },
  { value: 'couple', label: '연인과' },
  { value: 'friends', label: '친구와' },
  { value: 'family', label: '가족과' },
]
const moods = [
  { value: 'healing', label: '힐링', icon: '🌿' },
  { value: 'culture', label: '문화', icon: '🏛️' },
  { value: 'activity', label: '활동', icon: '🏃' },
  { value: 'night_view', label: '야경', icon: '🌙' },
  { value: 'shopping', label: '쇼핑', icon: '🛍️' },
]

const contentTypeIds = {
  관광지: 12,
  문화시설: 14,
  축제공연행사: 15,
  여행코스: 25,
  레포츠: 28,
  숙박: 32,
  쇼핑: 38,
  tourist_attraction: 12,
  cultural_facility: 14,
  festival_event: 15,
  travel_course: 25,
  leports: 28,
  accommodation: 32,
  shopping: 38,
}

const recommendations = computed(() => result.value?.data?.recommendations || [])

function selectDistrict(item) {
  district.value = item
  districtOpen.value = false
}

function closeDistrictOnOutsideClick(event) {
  if (!districtDropdown.value?.contains(event.target)) districtOpen.value = false
}

function requestLocation() {
  locationError.value = ''
  if (!navigator.geolocation) {
    locationStatus.value = 'unavailable'
    locationError.value = '이 브라우저에서는 현재 위치를 사용할 수 없어요.'
    return
  }
  locationStatus.value = 'requesting'
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      if (!Number.isFinite(coords.accuracy) || coords.accuracy > MAX_LOCATION_ACCURACY_METERS) {
        currentLocation.value = null
        locationStatus.value = 'inaccurate'
        locationError.value = '현재 위치가 너무 부정확해요. 지역을 직접 선택해 주세요.'
        mode.value = 'district'
        return
      }
      currentLocation.value = { latitude: coords.latitude, longitude: coords.longitude }
      locationStatus.value = 'granted'
    },
    (geoError) => {
      locationStatus.value = 'denied'
      locationError.value = geoError.code === 1
        ? '위치 권한이 거부됐어요. 지역 선택 추천을 이용해 주세요.'
        : '현재 위치를 확인하지 못했어요. 잠시 후 다시 시도해 주세요.'
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
  )
}

function buildPayload() {
  const common = {
    recommendation_mode: mode.value,
    available_minutes: availableMinutes.value,
    companion: companion.value,
    mood: mood.value,
  }
  return mode.value === 'nearby'
    ? { ...common, current_location: currentLocation.value }
    : { ...common, district: district.value }
}

async function submitRecommendation() {
  if (mode.value === 'nearby' && !currentLocation.value) {
    requestLocation()
    return
  }
  if (mode.value === 'district' && !district.value) return

  controller?.abort()
  const currentController = new AbortController()
  controller = currentController
  loading.value = true
  error.value = ''
  emit('results-change', false)
  emit('clear-course')
  try {
    const response = await getSituationalRecommendations(buildPayload(), currentController.signal)
    result.value = response
    emit('results-change', Boolean(response?.data?.recommendations?.length))
  } catch (requestError) {
    if (requestError.name === 'AbortError') return
    if (requestError.status === 404) error.value = '조건에 맞는 코스를 찾지 못했어요. 조건을 바꿔 다시 시도해 주세요.'
    else if (requestError.status === 422) error.value = '입력 조건을 확인해 주세요.'
    else error.value = requestError.message || '추천 코스를 불러오지 못했어요.'
  } finally {
    if (controller === currentController) loading.value = false
  }
}

function resetResult() {
  result.value = null
  error.value = ''
  emit('results-change', false)
  emit('clear-course')
}

function selectCourse(course) {
  if (props.selectedCourseId === course.id) emit('clear-course')
  else emit('select-course', course)
}

function courseKey(course, index) {
  return course.id ?? `${course.title}-${index}`
}

function categoryStyle(location) {
  const contentTypeId = location.content_type_id || contentTypeIds[location.content_type]
  const meta = getCategoryMeta(contentTypeId)
  return { background: meta.bg, color: meta.fg }
}

onMounted(() => document.addEventListener('pointerdown', closeDistrictOnOutsideClick))
onBeforeUnmount(() => {
  controller?.abort()
  document.removeEventListener('pointerdown', closeDistrictOnOutsideClick)
})
</script>

<template>
  <aside class="recommend-panel" aria-labelledby="recommend-title">
    <div class="recommend-head">
      <div>
        <span class="recommend-kicker">AI COURSE</span>
        <h2 id="recommend-title">상황별 여행코스 추천</h2>
      </div>
      <button v-if="result" type="button" class="recommend-back" @click="resetResult">조건 변경</button>
    </div>

    <form v-if="!result" class="recommend-form" @submit.prevent="submitRecommendation">
      <fieldset>
        <legend>어디를 기준으로 찾을까요?</legend>
        <div class="recommend-segment">
          <button type="button" :class="{ active: mode === 'nearby' }" @click="mode = 'nearby'">내 주변</button>
          <button type="button" :class="{ active: mode === 'district' }" @click="mode = 'district'">지역 선택</button>
        </div>
        <div v-if="mode === 'nearby'" class="location-permission">
          <button type="button" :disabled="locationStatus === 'requesting'" @click="requestLocation">
            {{ locationStatus === 'granted' ? '✓ 현재 위치 확인됨' : locationStatus === 'requesting' ? '위치 확인 중…' : '📍 현재 위치 사용하기' }}
          </button>
        </div>
        <div v-else ref="districtDropdown" class="recommend-dropdown" :class="{ open: districtOpen }">
          <button
            type="button"
            class="recommend-dropdown-trigger"
            aria-haspopup="listbox"
            :aria-expanded="districtOpen"
            @click="districtOpen = !districtOpen"
            @keydown.esc="districtOpen = false"
          >
            <span>{{ district }}</span>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5" /></svg>
          </button>
          <div v-if="districtOpen" class="recommend-dropdown-menu" role="listbox" aria-label="추천 지역">
            <button
              v-for="item in districts"
              :key="item"
              type="button"
              role="option"
              :aria-selected="district === item"
              :class="{ selected: district === item }"
              @click="selectDistrict(item)"
            >
              {{ item }}
            </button>
          </div>
        </div>
        <p v-if="locationError" class="location-guidance" role="status">{{ locationError }}</p>
      </fieldset>

      <fieldset>
        <legend>얼마나 시간이 있나요?</legend>
        <div class="recommend-options four">
          <button v-for="item in times" :key="item.value" type="button" :class="{ active: availableMinutes === item.value }" @click="availableMinutes = item.value">{{ item.label }}</button>
        </div>
      </fieldset>

      <fieldset>
        <legend>누구와 함께하나요?</legend>
        <div class="recommend-options four">
          <button v-for="item in companions" :key="item.value" type="button" :class="{ active: companion === item.value }" @click="companion = item.value">{{ item.label }}</button>
        </div>
      </fieldset>

      <fieldset>
        <legend>오늘 원하는 분위기는?</legend>
        <div class="recommend-options moods">
          <button v-for="item in moods" :key="item.value" type="button" :class="{ active: mood === item.value }" @click="mood = item.value">
            <span>{{ item.icon }}</span>{{ item.label }}
          </button>
        </div>
      </fieldset>

      <button class="recommend-submit" type="submit" :disabled="loading">
        {{ loading ? '코스를 만들고 있어요…' : '나에게 맞는 코스 추천받기' }}
      </button>
    </form>

    <div v-else class="recommend-results">
      <div v-if="result.meta?.fallback" class="recommend-banner">조건에 가장 가까운 대안 코스를 함께 보여드려요.</div>
      <p class="recommend-result-count">추천 코스 {{ recommendations.length }}개</p>

      <article
        v-for="(course, index) in recommendations"
        :key="courseKey(course, index)"
        class="course-card"
        :class="{ selected: selectedCourseId === course.id }"
        role="button"
        tabindex="0"
        :aria-pressed="selectedCourseId === course.id"
        @click="selectCourse(course)"
        @keydown.enter="selectCourse(course)"
        @keydown.space.prevent="selectCourse(course)"
      >
        <div class="course-heading">
          <div>
            <span class="course-index">COURSE {{ index + 1 }}</span>
            <h3>{{ course.title }}</h3>
          </div>
          <span class="course-count">장소 {{ course.estimated_place_count ?? course.locations?.length ?? 0 }}곳</span>
        </div>
        <p class="course-reason">{{ course.reason }}</p>
        <div class="course-summary">
          <span>⏱ 총 {{ course.estimated_duration_minutes }}분</span>
          <span>🚶 이동 {{ course.estimated_travel_minutes }}분</span>
          <span>📏 {{ course.estimated_distance_km }}km</span>
        </div>
        <div class="course-places">
          <button
            v-for="(location, locationIndex) in course.locations"
            :key="location.id"
            type="button"
            class="course-place"
            @click.stop="$emit('open-place', location)"
          >
            <div class="course-photo" :style="location.image_url ? { backgroundImage: `url(${location.image_url})` } : {}">
              <span class="course-order">{{ locationIndex + 1 }}</span>
              <small v-if="!location.image_url">NO IMAGE</small>
            </div>
            <strong>{{ location.title }}</strong>
            <span>{{ location.experience_type }} · 체류 약 {{ location.estimated_visit_minutes }}분</span>
            <small
              v-if="location.content_type"
              class="course-place-type"
              :style="categoryStyle(location)"
            >{{ location.content_type }}</small>
          </button>
        </div>
      </article>

      <div v-if="!recommendations.length" class="recommend-empty">
        <strong>추천 결과가 없어요.</strong>
        <span>조건을 바꿔 다시 추천받아 보세요.</span>
      </div>
    </div>

    <div v-if="error" class="recommend-error" role="alert">
      <p>{{ error }}</p>
      <button type="button" @click="submitRecommendation">다시 시도</button>
    </div>
  </aside>
</template>
