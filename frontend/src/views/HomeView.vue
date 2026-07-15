<script setup>
import { computed, ref } from 'vue'
import FilterChips from '../components/FilterChips.vue'
import LeafletMap from '../components/LeafletMap.vue'
import PlaceCard from '../components/PlaceCard.vue'
import { CATEGORIES, PLACES, SEOUL_DISTRICTS } from '../data/places.js'

const emit = defineEmits(['open-place', 'show-map'])
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

  <main class="home-layout">
    <section class="place-preview">
      <div class="section-summary">
        <span>전체 {{ filteredPlaces.length }}곳 중 일부</span>
        <button type="button" @click="$emit('show-map')">전체보기 ›</button>
      </div>

      <div v-if="filteredPlaces.length" class="place-list">
        <PlaceCard
          v-for="place in filteredPlaces.slice(0, 2)"
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

    <LeafletMap :places="filteredPlaces" @open-place="emit('open-place', $event)" />
  </main>
</template>
