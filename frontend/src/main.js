import { createApp } from 'vue'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import './style.css'
import App from './App.vue'
import router from './router/index.js'

createApp(App).use(router).mount('#app')
