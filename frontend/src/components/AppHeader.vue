<script setup>
defineProps({
  currentView: { type: String, required: true },
})

defineEmits(['navigate'])

const items = [
  { key: 'home', label: '탐색' },
  { key: 'map', label: '지도' },
  { key: 'community', label: '커뮤니티' },
]
</script>

<template>
  <header class="app-header">
    <button class="brand" type="button" @click="$emit('navigate', 'home')">
      <strong>TeumSeoul</strong>
      <span>서울 통합 탐색</span>
    </button>

    <nav aria-label="주요 메뉴">
      <button
        v-for="item in items"
        :key="item.key"
        type="button"
        :class="{ active: currentView === item.key }"
        @click="$emit('navigate', item.key)"
      >
        {{ item.label }}
      </button>
    </nav>
    <div class="header-spacer" />
  </header>
</template>
