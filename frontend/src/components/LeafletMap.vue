<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet.markercluster'
import { getCategoryMeta } from '../utils/category.js'

const props = defineProps({
  places: { type: Array, required: true },
  categories: { type: Array, required: true },
  height: { type: String, default: '520px' },
})

const emit = defineEmits(['open-place', 'bounds-change'])
const mapElement = ref(null)
const clusterEnabled = ref(true)
const markerLayer = L.layerGroup()
let clusterLayer
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
  clusterLayer.clearLayers()

  props.places.forEach((place) => {
    const marker = L.marker([place.latitude, place.longitude], { icon: markerIcon(place) })
      .bindTooltip(place.title, { direction: 'top', offset: [0, -24] })
      .on('click', () => emit('open-place', place))
    if (clusterEnabled.value) clusterLayer.addLayer(marker)
    else markerLayer.addLayer(marker)
  })
}

function setClusterEnabled(enabled) {
  clusterEnabled.value = enabled
  if (!map) return

  map.removeLayer(markerLayer)
  map.removeLayer(clusterLayer)
  ;(enabled ? clusterLayer : markerLayer).addTo(map)
  renderMarkers()
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
  clusterLayer = L.markerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 52,
  }).addTo(map)
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
    <label class="cluster-toggle">
      <span>Cluster</span>
      <input
        :checked="clusterEnabled"
        type="checkbox"
        role="switch"
        aria-label="지도 마커 클러스터 사용"
        @change="setClusterEnabled($event.target.checked)"
      />
      <span class="toggle-track" aria-hidden="true"><span /></span>
      <strong>{{ clusterEnabled ? 'ON' : 'OFF' }}</strong>
    </label>
    <div class="map-legend">
      <div v-for="category in categories" :key="category.id">
        <span :style="{ background: getCategoryMeta(category.id).dot }" />
        {{ category.name }}
      </div>
    </div>
  </div>
</template>
