<script setup>
import { ref, computed } from 'vue'
import LeafletMap from '../components/LeafletMap.vue'
import PostDetailView from './PostDetailView.vue'
import { SEOUL_DISTRICTS, PLACES } from '../data/places.js'

const WRITE_STATUS_TAGS = [
  { label: '혼잡', key: 'crowded' },
  { label: '여유', key: 'relaxed' },
  { label: '공사', key: 'construction' },
  { label: '이용 주의', key: 'caution' },
  { label: '사진 추천', key: 'photo' },
  { label: '가족 추천', key: 'family' },
  { label: '혼자 추천', key: 'solo' },
]

const WRITE_CATEGORIES = [
  { label: '현장 제보', key: 'report' },
  { label: '방문 후기', key: 'review' },
]

const communityCats = ref([
  { label: '전체', key: 'all' },
  { label: '현장 제보', key: 'report' },
  { label: '방문 후기', key: 'review' },
])

const communityDistricts = ref(
  [{ label: '전체', key: 'all' }, ...SEOUL_DISTRICTS.map((d) => ({ label: d, key: d }))],
)

const posts = ref([
  {
    id: 1,
    category: '현장 제보',
    title: '벚꽃 예쁜 카페 추천해주세요',
    time: '2시간전',
    views: 123,
    placeName: '북촌카페',
    statusTags: ['혼잡', '사진 추천'],
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
    statusTags: ['이용 주의'],
    district: '중구',
  },
])

const isWrite = ref(false)
const isEditing = ref(false)
const editingPostId = ref(null)
const selectedPost = ref(null)
const selectedCategory = ref('all')
const selectedDistrict = ref('all')
const communitySearchQuery = ref('')
const pageSize = 20
const currentPage = ref(1)
const selectedWriteCategory = ref('report')
const selectedStatusTags = ref([])
const draftTitle = ref('')
const draftBody = ref('')
const draftPassword = ref('')
const draftPlaceName = ref('')
const selectedWritePlace = ref(null)
const writePlaces = ref(PLACES.slice(0, 6))
const writeSubmitLabel = ref('등록')

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

const selectedWritePlaceName = computed(() => draftPlaceName.value || selectedWritePlace.value?.title || '')

function goWrite() {
  isWrite.value = true
  selectedPost.value = null
  resetDraft()
}

function backToCommunity() {
  isWrite.value = false
  selectedPost.value = null
  resetDraft()
}

function resetDraft() {
  isEditing.value = false
  editingPostId.value = null
  selectedWriteCategory.value = 'report'
  selectedStatusTags.value = []
  draftTitle.value = ''
  draftBody.value = ''
  draftPassword.value = ''
  draftPlaceName.value = ''
  selectedWritePlace.value = null
  writeSubmitLabel.value = '등록'
}

function getCategoryKey(categoryLabel) {
  return WRITE_CATEGORIES.find((cat) => cat.label === categoryLabel)?.key || 'report'
}

function getStatusTagKeys(statusLabels = []) {
  return statusLabels
    .map((label) => WRITE_STATUS_TAGS.find((tag) => tag.label === label)?.key)
    .filter(Boolean)
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
  selectedPost.value = post
}

function handlePostEdit(post) {
  isWrite.value = true
  selectedPost.value = null
  isEditing.value = true
  editingPostId.value = post.id
  writeSubmitLabel.value = '수정 완료'
  selectedWriteCategory.value = getCategoryKey(post.category)
  selectedStatusTags.value = getStatusTagKeys(post.statusTags || [])
  draftTitle.value = post.title || ''
  draftBody.value = post.body || ''
  draftPassword.value = ''
  draftPlaceName.value = post.placeName || ''
  selectedWritePlace.value = PLACES.find((place) => place.title === post.placeName) || null
}

function handlePostDelete(post) {
  console.log('delete', post)
}

function toggleStatusTag(tagKey) {
  if (selectedStatusTags.value.includes(tagKey)) {
    selectedStatusTags.value = selectedStatusTags.value.filter((key) => key !== tagKey)
    return
  }
  selectedStatusTags.value = [...selectedStatusTags.value, tagKey]
}

function selectWriteCategory(key) {
  selectedWriteCategory.value = key
}

function handleWritePlaceSelect(place) {
  selectedWritePlace.value = place
  draftPlaceName.value = place.title
}

function setCommunitySearchQuery(e) {
  communitySearchQuery.value = e.target.value
  currentPage.value = 1
}

function goPage(n) {
  currentPage.value = n
}

function submitPost() {
  const title = draftTitle.value.trim()
  const body = draftBody.value.trim()
  const password = draftPassword.value.trim()

  if (!title || !draftPlaceName.value || !body || !password) {
    alert('제목, 장소, 내용, 비밀번호를 모두 입력해주세요.')
    return
  }

  const categoryLabel = WRITE_CATEGORIES.find((cat) => cat.key === selectedWriteCategory.value)?.label || '현장 제보'
  const statusLabels = selectedStatusTags.value.map((tagKey) => {
    return WRITE_STATUS_TAGS.find((tag) => tag.key === tagKey)?.label || tagKey
  })

  if (isEditing.value && editingPostId.value) {
    const targetIndex = posts.value.findIndex((post) => post.id === editingPostId.value)
    if (targetIndex !== -1) {
      posts.value[targetIndex] = {
        ...posts.value[targetIndex],
        category: categoryLabel,
        title,
        placeName: draftPlaceName.value,
        statusTags: statusLabels,
        district: selectedWritePlace.value?.district || '미지정',
        body,
      }
    }
  } else {
    posts.value.unshift({
      id: Date.now(),
      category: categoryLabel,
      title,
      time: '방금 전',
      views: 0,
      placeName: draftPlaceName.value,
      statusTags: statusLabels,
      district: selectedWritePlace.value?.district || '미지정',
      body,
      author: '익명',
    })
  }

  backToCommunity()
  currentPage.value = 1
}
</script>

<template>
  <div class="community-container">
    <template v-if="isWrite">
      <div class="community-write-screen">
        <button class="community-write-back" type="button" @click="backToCommunity">← 커뮤니티로 돌아가기</button>
        <h2 class="community-write-title">새 글 작성</h2>

        <div class="community-write-form">
          <div class="community-write-map-card">
            <div class="community-write-map-tip">지도에서 장소를 선택하세요</div>
            <div class="community-write-map-shell">
              <LeafletMap :places="writePlaces" height="280px" @open-place="handleWritePlaceSelect" />
            </div>
          </div>

          <input
            v-model="draftTitle"
            type="text"
            class="community-write-input"
            placeholder="제목을 입력하세요"
          />

          <input
            :value="selectedWritePlaceName"
            type="text"
            class="community-write-input community-write-input-disabled"
            placeholder="지도에서 선택한 장소"
            disabled
          />

          <div>
            <div class="community-write-section-label">상태 태그 선택 (선택, 복수 가능)</div>
            <div class="chip-row write-chip-row">
              <button
                v-for="tag in WRITE_STATUS_TAGS"
                :key="tag.key"
                type="button"
                class="write-chip"
                :class="{ active: selectedStatusTags.includes(tag.key) }"
                @click="toggleStatusTag(tag.key)"
              >
                {{ tag.label }}
              </button>
            </div>
          </div>

          <textarea
            v-model="draftBody"
            class="community-write-textarea"
            placeholder="내용을 입력하세요"
          />

          <div class="chip-row write-chip-row">
            <button
              v-for="cat in WRITE_CATEGORIES"
              :key="cat.key"
              type="button"
              class="write-chip"
              :class="{ active: selectedWriteCategory === cat.key }"
              @click="selectWriteCategory(cat.key)"
            >
              {{ cat.label }}
            </button>
          </div>

          <input
            v-model="draftPassword"
            type="password"
            class="community-write-input"
            placeholder="비밀번호 (글 수정·삭제 시 필요)"
          />

          <button class="community-submit-btn" type="button" @click="submitPost">{{ writeSubmitLabel }}</button>
        </div>
      </div>
    </template>

    <template v-else-if="selectedPost">
      <PostDetailView :post="selectedPost" @back="backToCommunity" @edit="handlePostEdit" @delete="handlePostDelete" />
    </template>

    <template v-else>
      <div class="community-header">
        <h1>커뮤니티</h1>
        <button class="write-btn" type="button" @click="goWrite">+ 글쓰기</button>
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
    </template>
  </div>
</template>
