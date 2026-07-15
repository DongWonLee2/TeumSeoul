<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet.markercluster'
import { getCategoryMeta } from '../utils/category.js'

const props = defineProps({
  places: { type: Array, required: true },
  categories: { type: Array, required: true },
  height: { type: String, default: '520px' },
  loading: { type: Boolean, default: false },
  fitRequest: { type: Number, default: 0 },
  focusPlace: { type: Object, default: null },
  focusRequest: { type: Number, default: 0 },
})

const emit = defineEmits(['open-place', 'bounds-change'])
const mapElement = ref(null)
const clusterEnabled = ref(true)
const markerLayer = L.layerGroup()
let clusterLayer
let map

const mapStyle = computed(() => ({ minHeight: props.height }))
const courseMode = computed(() => props.places.some((place) => place.courseOrder))

function markerIcon(place) {
  const meta = getCategoryMeta(place.content_type_id)
  if (place.courseOrder) {
    return L.divIcon({
      className: 'teum-course-marker-wrapper',
      html: `<svg class="teum-course-marker" viewBox="0 0 36 44" aria-hidden="true">
        <path d="M18 1.5C8.9 1.5 1.5 8.9 1.5 18c0 11.8 16.5 24.5 16.5 24.5S34.5 29.8 34.5 18C34.5 8.9 27.1 1.5 18 1.5Z" fill="${meta.dot}" stroke="white" stroke-width="3" stroke-linejoin="round"/>
        <text x="18" y="23" text-anchor="middle" fill="white" font-size="14" font-weight="900" font-family="Noto Sans KR, sans-serif">${place.courseOrder}</text>
      </svg>`,
      iconSize: [36, 44],
      iconAnchor: [18, 43],
    })
  }
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

  const validPlaces = props.places
    .filter((place) => Number.isFinite(place.latitude) && Number.isFinite(place.longitude))
  const clusterIndexes = clusterEnabled.value && !courseMode.value
    ? findClusterIndexes(validPlaces)
    : new Set()
  const clusteredMarkers = []

  validPlaces.forEach((place, index) => {
    const marker = L.marker([place.latitude, place.longitude], { icon: markerIcon(place) })
      .bindTooltip(place.title, { direction: 'top', offset: [0, -24] })
      .on('click', () => emit('open-place', place))
    if (clusterIndexes.has(index)) {
      clusterLayer.addLayer(marker)
      clusteredMarkers.push(marker)
    }
    else markerLayer.addLayer(marker)
  })

  const smallClusterMarkers = clusteredMarkers.filter((marker) => {
    const visibleParent = clusterLayer.getVisibleParent(marker)
    return typeof visibleParent?.getChildCount === 'function' && visibleParent.getChildCount() < 3
  })
  smallClusterMarkers.forEach((marker) => {
    clusterLayer.removeLayer(marker)
    markerLayer.addLayer(marker)
  })
}

function findClusterIndexes(places) {
  const parent = places.map((_, index) => index)
  const points = places.map((place) => map.latLngToLayerPoint([place.latitude, place.longitude]))

  function find(index) {
    while (parent[index] !== index) {
      parent[index] = parent[parent[index]]
      index = parent[index]
    }
    return index
  }

  function union(a, b) {
    const rootA = find(a)
    const rootB = find(b)
    if (rootA !== rootB) parent[rootB] = rootA
  }

  for (let i = 0; i < points.length; i += 1) {
    for (let j = i + 1; j < points.length; j += 1) {
      if (points[i].distanceTo(points[j]) <= 52) union(i, j)
    }
  }

  const groupSizes = new Map()
  places.forEach((_, index) => {
    const root = find(index)
    groupSizes.set(root, (groupSizes.get(root) || 0) + 1)
  })

  return new Set(
    places.map((_, index) => index).filter((index) => groupSizes.get(find(index)) >= 3),
  )
}

function syncVisibleLayer() {
  if (!map || !clusterLayer) return
  map.removeLayer(markerLayer)
  map.removeLayer(clusterLayer)
  markerLayer.addTo(map)
  if (clusterEnabled.value && !courseMode.value) clusterLayer.addTo(map)
}

function setClusterEnabled(enabled) {
  clusterEnabled.value = enabled
  if (!map) return

  syncVisibleLayer()
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

function fitPlaces() {
  if (!map) return
  const coordinates = props.places
    .filter((place) => Number.isFinite(place.latitude) && Number.isFinite(place.longitude))
    .map((place) => [place.latitude, place.longitude])
  if (!coordinates.length) return
  if (coordinates.length === 1) map.setView(coordinates[0], 15)
  else map.fitBounds(coordinates, { padding: [36, 36], maxZoom: 15 })
}

function focusPlace() {
  const place = props.focusPlace
  if (!map || !place || !Number.isFinite(place.latitude) || !Number.isFinite(place.longitude)) return
  map.setView([place.latitude, place.longitude], Math.max(map.getZoom(), 16), { animate: true })
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
  })
  syncVisibleLayer()
  renderMarkers()
  map.on('moveend', emitBounds)
  map.on('zoomend', renderMarkers)
  emitBounds()
})

watch(() => props.places, () => {
  syncVisibleLayer()
  renderMarkers()
}, { deep: true })
watch(() => props.fitRequest, async () => {
  await nextTick()
  fitPlaces()
})
watch(() => props.focusRequest, async () => {
  await nextTick()
  focusPlace()
})

onBeforeUnmount(() => {
  map?.remove()
  map = null
})
</script>

<template>
  <div class="map-frame" :style="mapStyle">
    <div ref="mapElement" class="leaflet-map" />
    <div v-if="loading" class="map-loading" role="status">지도 장소를 불러오는 중…</div>
    <label v-if="!courseMode" class="cluster-toggle">
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
