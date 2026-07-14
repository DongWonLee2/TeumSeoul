<script setup>
import { computed } from 'vue'
import { getCategoryMeta } from '../utils/category.js'

const props = defineProps({
  place: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})

defineEmits(['open'])

const meta = computed(() => getCategoryMeta(props.place.category))
const photoStyle = computed(() => ({
  backgroundImage: props.place.image_url
    ? `url(${props.place.image_url})`
    : `repeating-linear-gradient(45deg, ${meta.value.bg} 0 8px, ${meta.value.stripe} 8px 16px)`,
}))
</script>

<template>
  <button
    type="button"
    class="place-card"
    :class="{ compact }"
    @click="$emit('open', place)"
  >
    <div class="place-photo" :style="photoStyle">
      <span v-if="!place.image_url" :style="{ color: meta.fg }">PHOTO</span>
    </div>
    <div class="place-card-content">
      <div class="place-card-meta">
        <span class="category-badge" :style="{ background: meta.bg, color: meta.fg }">
          {{ place.content_type }}
        </span>
        <span>{{ place.district }}</span>
      </div>
      <strong>{{ place.title }}</strong>
      <div class="place-stats">
        <span v-if="place.rating">⭐ {{ place.rating }}</span>
        <span v-if="!compact" class="post-count">💬 게시글 {{ place.related_post_count }}건</span>
      </div>
    </div>
  </button>
</template>
