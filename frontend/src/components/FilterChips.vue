<script setup>
defineProps({
  searchQuery: { type: String, required: true },
  categories: { type: Array, required: true },
  districts: { type: Array, required: true },
  activeCategory: { type: String, required: true },
  activeDistrict: { type: String, required: true },
})

defineEmits(['update:searchQuery', 'select-category', 'select-district'])
</script>

<template>
  <section class="filter-panel" aria-label="장소 검색 필터">
    <input
      :value="searchQuery"
      type="search"
      placeholder="장소, 지역, 축제 이름으로 검색"
      aria-label="장소 검색"
      @input="$emit('update:searchQuery', $event.target.value)"
    />

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
        :key="category.key"
        type="button"
        class="filter-chip category-chip"
        :class="{ active: activeCategory === category.key }"
        @click="$emit('select-category', category.key)"
      >
        {{ category.label }}
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
