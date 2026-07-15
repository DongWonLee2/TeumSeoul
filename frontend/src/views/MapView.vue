<script setup>
import { computed, ref } from 'vue'
import FilterChips from '../components/FilterChips.vue'
import LeafletMap from '../components/LeafletMap.vue'
import PlaceCard from '../components/PlaceCard.vue'
import { CATEGORIES, PLACES, SEOUL_DISTRICTS } from '../data/places.js'

defineEmits(['open-place'])

const searchQuery = ref('')
const activeCategory = ref('all')
const activeDistrict = ref('all')

const filteredPlaces = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return PLACES.filter((place) => {
    const categoryMatches = activeCategory.value === 'all' || place.content_type_id === activeCategory.value
    const districtMatches = activeDistrict.value === 'all' || place.district === activeDistrict.value
    const queryMatches = !query
      || place.title.toLowerCase().includes(query)
      || place.district.toLowerCase().includes(query)
      || place.address.toLowerCase().includes(query)
    return categoryMatches && districtMatches && queryMatches
  })
})
</script>

<template>
  <FilterChips
    v-model:search-query="searchQuery"
    :categories="CATEGORIES"
    :districts="SEOUL_DISTRICTS"
    :active-category="activeCategory"
    :active-district="activeDistrict"
    @select-category="activeCategory = $event"
    @select-district="activeDistrict = $event"
  />

  <main class="map-page">
    <div class="map-title">
      <h1>지도</h1>
      <span>전체 {{ filteredPlaces.length }}곳</span>
    </div>

    <LeafletMap
      :places="filteredPlaces"
      height="min(640px, 70vh)"
      @open-place="$emit('open-place', $event)"
    />

    <div v-if="filteredPlaces.length" class="map-card-row">
      <PlaceCard
        v-for="place in filteredPlaces"
        :key="place.id"
        :place="place"
        compact
        @open="$emit('open-place', $event)"
      />
    </div>
    <div v-else class="empty-results map-empty">
      <strong>검색 결과가 없어요</strong>
      <span>필터를 바꾸면 지도 마커가 다시 표시됩니다.</span>
    </div>
  </main>
</template>
