import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import MapView from '../views/MapView.vue'
import CommunityView from '../views/CommunityView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView, meta: { section: 'home' } },
    { path: '/map', name: 'map', component: MapView, meta: { section: 'map' } },
    {
      path: '/places/:id',
      name: 'place-detail',
      component: HomeView,
      meta: { section: 'home', placeModal: true },
    },
    {
      path: '/map/places/:id',
      name: 'map-place-detail',
      component: MapView,
      meta: { section: 'map', placeModal: true },
    },
    {
      path: '/community',
      name: 'community',
      component: CommunityView,
      meta: { section: 'community' },
    },
    {
      path: '/community/places/:id',
      name: 'community-place-detail',
      component: CommunityView,
      meta: { section: 'community', placeModal: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

const PLACE_DETAIL_ROUTE_NAMES = {
  map: 'map-place-detail',
  community: 'community-place-detail',
  home: 'place-detail',
}

export function placeDetailRouteName(section) {
  return PLACE_DETAIL_ROUTE_NAMES[section] || 'place-detail'
}

export default router
