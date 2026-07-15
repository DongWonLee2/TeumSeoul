<script setup>
defineProps({
  searchQuery: { type: String, required: true },
  categories: { type: Array, required: true },
  districts: { type: Array, required: true },
  activeCategory: { type: [String, Number], required: true },
  activeDistrict: { type: String, required: true },
})

defineEmits(['update:searchQuery', 'select-category', 'select-district', 'search'])
</script>

<template>
  <section class="filter-panel" aria-label="장소 검색 필터">
    <form class="filter-search" role="search" @submit.prevent="$emit('search')">
      <input
        :value="searchQuery"
        type="search"
        placeholder="장소, 지역, 축제 이름으로 검색"
        aria-label="장소 검색"
        @input="$emit('update:searchQuery', $event.target.value)"
      />
      <button type="submit" class="search-submit">검색</button>
    </form>

    <div class="chip-row">
      <button
        type="button"
        class="filter-chip category-chip"
        :class="{ active: activeCategory === 'all' }"
        @click="$emit('select-category', 'all')"
      >
        전체
      </button>
      <button
        v-for="category in categories"
        :key="category.id"
        type="button"
        class="filter-chip category-chip"
        :class="{ active: activeCategory === category.id }"
        @click="$emit('select-category', category.id)"
      >
        {{ category.name }}
      </button>
    </div>

    <div class="chip-row">
      <button
        type="button"
        class="filter-chip district-chip"
        :class="{ active: activeDistrict === 'all' }"
        @click="$emit('select-district', 'all')"
      >
        전체 자치구
      </button>
      <button
        v-for="district in districts"
        :key="district"
        type="button"
        class="filter-chip district-chip"
        :class="{ active: activeDistrict === district }"
        @click="$emit('select-district', district)"
      >
        {{ district }}
      </button>
    </div>
  </section>
</template>
