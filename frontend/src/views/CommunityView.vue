<script setup>
import { ref, computed } from 'vue'
import AppHeader from '../components/AppHeader.vue'
import { SEOUL_DISTRICTS } from '../data/places.js'

const communityCats = ref([
  { label: '전체', key: 'all' },
  { label: '현장 제보', key: 'report' },
  { label: '방문 후기', key: 'review' },
])

const communityDistricts = ref(
  [{ label: '전체', key: 'all' }, ...SEOUL_DISTRICTS.map(d => ({ label: d, key: d }))]
)


const posts = ref([
  {
    id: 1,
    category: '현장 제보',
    title: '벚꽃 예쁜 카페 추천해주세요',
    time: '2시간전',
    views: 123,
    placeName: '북촌카페',
    statusTags: ['추천', '핫'],
    district: '종로구',
  },
  {
    id: 2,
    category: '방문 후기',
    title: '주말에 하이킹 같이 가실 분?',
    time: '1일전',
    views: 45,
    placeName: '북한산',
    statusTags: [],
    district: '강북구',
  },
  {
    id: 3,
    category: '현장 제보',
    title: '서울시 무료 전시 정보 어디서 보나요?',
    time: '3일전',
    views: 78,
    placeName: '시립미술관',
    statusTags: ['정보'],
    district: '중구',
  },
])

const selectedCategory = ref('all')
const selectedDistrict = ref('all')
const communitySearchQuery = ref('')
const pageSize = 20
const currentPage = ref(1)

const filtered = computed(() => {
  return posts.value.filter((p) => {
    if (selectedCategory.value !== 'all' && p.category !== selectedCategory.value) return false
    if (selectedDistrict.value !== 'all' && p.district !== selectedDistrict.value) return false
    if (communitySearchQuery.value && !p.title.includes(communitySearchQuery.value)) return false
    return true
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)))

const communityPostsPage = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

function goWrite() {
  // placeholder: in a real app you'd navigate to a write route
  alert('글쓰기 화면으로 이동(예시)')
}

function selectCategory(cat) {
  selectedCategory.value = cat.key
  currentPage.value = 1
}

function selectDistrict(d) {
  selectedDistrict.value = d.key
  currentPage.value = 1
}

function openPost(post) {
  alert(`열기: ${post.title}`)
}

function deletePost(post) {
  const idx = posts.value.findIndex((p) => p.id === post.id)
  if (idx !== -1) posts.value.splice(idx, 1)
}

function setCommunitySearchQuery(e) {
  communitySearchQuery.value = e.target.value
  currentPage.value = 1
}

function goPage(n) {
  currentPage.value = n
}
</script>

<template>
  <div class="community-container">
    <div class="community-header">
      <h1>커뮤니티</h1>
      <button class="write-btn" @click="goWrite">+ 글쓰기</button>
    </div>

    <div class="community-filter-row">
      <div class="chip-row">
        <button 
          v-for="pc in communityCats" 
          :key="pc.key" 
          @click="selectCategory(pc)"
          :class="['filter-chip', 'category-chip', { active: selectedCategory === pc.key }]"
        >
          {{ pc.label }}
        </button>
      </div>

      <div class="chip-row">
        <button 
          v-for="cd in communityDistricts" 
          :key="cd.key" 
          @click="selectDistrict(cd)"
          :class="['filter-chip', 'district-chip', { active: selectedDistrict === cd.key }]"
        >
          {{ cd.label }}
        </button>
      </div>
    </div>

    <div class="posts-container">
      <div v-for="post in communityPostsPage" :key="post.id" class="post-item">
        <div class="post-content" @click="openPost(post)">
          <div class="post-header">
            <span class="post-category">{{ post.category }}</span>
            <span class="post-title">{{ post.title }}</span>
          </div>
          <div class="post-meta">익명 · {{ post.time }} · 조회 {{ post.views }} · 📍 {{ post.placeName }}</div>

          <div v-if="post.statusTags && post.statusTags.length" class="status-tags">
            <span v-for="stg in post.statusTags" :key="stg" class="status-tag">{{ stg }}</span>
          </div>
        </div>
      </div>

      <div v-if="!filtered.length" class="empty-results">검색 결과가 없어요</div>
    </div>

    <div class="pagination">
      <button 
        v-for="n in totalPages" 
        :key="n" 
        @click="goPage(n)"
        :class="['page-btn', { active: currentPage === n }]"
      >
        {{ n }}
      </button>
    </div>

    <div class="search-container">
      <input 
        type="text" 
        placeholder="게시글 제목 검색" 
        :value="communitySearchQuery" 
        @input="setCommunitySearchQuery"
        class="search-input"
      />
      <span class="search-icon">🔍</span>
    </div>
  </div>
</template>

<style scoped>
/* Styles are defined in the global style.css */
</style>
