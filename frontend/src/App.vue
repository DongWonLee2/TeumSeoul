<script setup>
import { computed, ref } from 'vue'
import AppHeader from './components/AppHeader.vue'
import PlaceModal from './components/PlaceModal.vue'
import HomeView from './views/HomeView.vue'
import MapView from './views/MapView.vue'
import CommunityView from './views/CommunityView.vue'
import { PLACES } from './data/places.js'

const currentView = ref('home')
const selectedPlaceId = ref(null)

const selectedPlace = computed(() =>
  PLACES.find((place) => place.id === selectedPlaceId.value),
)

function openPlace(place) {
  selectedPlaceId.value = place.id
}
</script>

<template>
  <div class="app-shell">
    <AppHeader :current-view="currentView" @navigate="currentView = $event" />

    <HomeView
      v-if="currentView === 'home'"
      @open-place="openPlace"
      @show-map="currentView = 'map'"
    />
    <MapView v-else-if="currentView === 'map'" @open-place="openPlace" />
    <CommunityView v-else-if="currentView === 'community'" />

    <PlaceModal
      v-if="selectedPlace"
      :place="selectedPlace"
      @close="selectedPlaceId = null"
    />
  </div>
</template>
