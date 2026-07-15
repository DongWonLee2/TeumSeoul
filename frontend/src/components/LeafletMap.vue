<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import { CATEGORIES } from '../data/places.js'
import { getCategoryMeta } from '../utils/category.js'

const props = defineProps({
  places: { type: Array, required: true },
  height: { type: String, default: '520px' },
})

const emit = defineEmits(['open-place', 'bounds-change'])
const mapElement = ref(null)
const markerLayer = L.layerGroup()
let map

const mapStyle = computed(() => ({ minHeight: props.height }))

function markerIcon(place) {
  const meta = getCategoryMeta(place.content_type_id)
  return L.divIcon({
    className: 'teum-marker-wrapper',
    html: `<span class="teum-marker" style="background:${meta.dot}"></span>`,
    iconSize: [22, 28],
    iconAnchor: [11, 28],
  })
}

function renderMarkers() {
  if (!map) return
  markerLayer.clearLayers()

  props.places.forEach((place) => {
    const marker = L.marker([place.latitude, place.longitude], { icon: markerIcon(place) })
      .bindTooltip(place.title, { direction: 'top', offset: [0, -24] })
      .on('click', () => emit('open-place', place))
    markerLayer.addLayer(marker)
  })
}

function emitBounds() {
  const bounds = map.getBounds()
  emit('bounds-change', {
    south: bounds.getSouth(),
    west: bounds.getWest(),
    north: bounds.getNorth(),
    east: bounds.getEast(),
  })
}

onMounted(async () => {
  await nextTick()
  map = L.map(mapElement.value, { zoomControl: false }).setView([37.5665, 126.978], 12)
  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map)
  markerLayer.addTo(map)
  renderMarkers()
  map.on('moveend', emitBounds)
})

watch(() => props.places, renderMarkers, { deep: true })

onBeforeUnmount(() => {
  map?.remove()
  map = null
})
</script>

<template>
  <div class="map-frame" :style="mapStyle">
    <div ref="mapElement" class="leaflet-map" />
    <div class="map-legend">
      <div v-for="category in CATEGORIES" :key="category.id">
        <span :style="{ background: getCategoryMeta(category.id).dot }" />
        {{ category.name }}
      </div>
    </div>
  </div>
</template>
