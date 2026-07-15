<script setup>
import { onBeforeUnmount } from 'vue'

defineProps({
  searchQuery: { type: String, required: true },
  categories: { type: Array, required: true },
  districts: { type: Array, required: true },
  activeCategory: { type: [String, Number], required: true },
  activeDistrict: { type: String, required: true },
})

const emit = defineEmits(['update:searchQuery', 'select-category', 'select-district', 'search'])

const SEARCH_DEBOUNCE_MS = 400
let searchTimer

function clearSearchTimer() {
  if (!searchTimer) return
  clearTimeout(searchTimer)
  searchTimer = undefined
}

function scheduleSearch() {
  clearSearchTimer()
  searchTimer = setTimeout(() => {
    searchTimer = undefined
    emit('search')
  }, SEARCH_DEBOUNCE_MS)
}

function handleInput(event) {
  emit('update:searchQuery', event.target.value)
  scheduleSearch()
}

function selectCategory(category) {
  clearSearchTimer()
  emit('select-category', category)
  emit('search')
}

function selectDistrict(district) {
  clearSearchTimer()
  emit('select-district', district)
  emit('search')
}

function submitSearch() {
  clearSearchTimer()
  emit('search')
}

onBeforeUnmount(clearSearchTimer)
</script>

<template>
  <section class="filter-panel" aria-label="장소 검색 필터">
    <form class="filter-search" role="search" @submit.prevent="submitSearch">
      <input
        :value="searchQuery"
        type="search"
        placeholder="장소, 지역, 축제 이름으로 검색"
        aria-label="장소 검색"
        @input="handleInput"
      />
      <button type="submit" class="search-submit">검색</button>
    </form>

    <div class="chip-row">
      <button
        type="button"
        class="filter-chip category-chip"
        :class="{ active: activeCategory === 'all' }"
        @click="selectCategory('all')"
      >
        전체
      </button>
      <button
        v-for="category in categories"
        :key="category.id"
        type="button"
        class="filter-chip category-chip"
        :class="{ active: activeCategory === category.id }"
        @click="selectCategory(category.id)"
      >
        {{ category.name }}
      </button>
    </div>

    <div class="chip-row">
      <button
        type="button"
        class="filter-chip district-chip"
        :class="{ active: activeDistrict === 'all' }"
        @click="selectDistrict('all')"
      >
        전체 자치구
      </button>
      <button
        v-for="district in districts"
        :key="district"
        type="button"
        class="filter-chip district-chip"
        :class="{ active: activeDistrict === district }"
        @click="selectDistrict(district)"
      >
        {{ district }}
      </button>
    </div>
  </section>
</template>
