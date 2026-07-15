<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getCategoryMeta } from '../utils/category.js'

const props = defineProps({
  place: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['open', 'need-address'])
const cardElement = ref(null)
let addressObserver

const meta = computed(() => getCategoryMeta(props.place.content_type_id))
const thumbnailUrl = computed(() => props.place.thumbnail_url || props.place.image_url)
const photoStyle = computed(() => ({
  backgroundImage: thumbnailUrl.value
    ? `url(${thumbnailUrl.value})`
    : `repeating-linear-gradient(45deg, ${meta.value.bg} 0 8px, ${meta.value.stripe} 8px 16px)`,
}))

onMounted(() => {
  if (props.place.address) return
  if (!('IntersectionObserver' in window)) {
    emit('need-address', props.place)
    return
  }

  addressObserver = new IntersectionObserver(([entry]) => {
    if (!entry.isIntersecting) return
    emit('need-address', props.place)
    addressObserver.disconnect()
  }, { threshold: 0.15 })
  addressObserver.observe(cardElement.value)
})

onBeforeUnmount(() => addressObserver?.disconnect())
</script>

<template>
  <button
    ref="cardElement"
    type="button"
    class="place-card"
    :class="{ compact }"
    @click="$emit('open', place)"
  >
    <div class="place-photo" :style="photoStyle">
      <span v-if="!thumbnailUrl" :style="{ color: meta.fg }">PHOTO</span>
    </div>
    <div class="place-card-content">
      <div class="place-card-meta">
        <span class="category-badge" :style="{ background: meta.bg, color: meta.fg }">
          {{ place.content_type }}
        </span>
        <span>{{ place.district }}</span>
      </div>
      <strong>{{ place.title }}</strong>
      <span v-if="place.address" class="place-card-address">📍 {{ place.address }}</span>
    </div>
  </button>
</template>
