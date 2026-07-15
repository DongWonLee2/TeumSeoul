<script setup>
import { ref, computed, onMounted } from 'vue'
import LeafletMap from '../components/LeafletMap.vue'
import PostDetailView from './PostDetailView.vue'
import { SEOUL_DISTRICTS, PLACES } from '../data/places.js'
import { createPost, deletePost, getPostDetail, getPosts, updatePost } from '../api/posts.js'

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

const posts = ref([])
const isLoading = ref(false)
const isSubmitting = ref(false)
const loadError = ref('')
const currentPage = ref(1)
const totalPages = ref(1)
const totalItems = ref(0)
const pageSize = 20

const isWrite = ref(false)
const isEditing = ref(false)
const editingPostId = ref(null)
const selectedPost = ref(null)
const selectedCategory = ref('all')
const selectedDistrict = ref('all')
const communitySearchQuery = ref('')
const selectedWriteCategory = ref('report')
const selectedStatusTags = ref([])
const draftTitle = ref('')
const draftBody = ref('')
const draftPassword = ref('')
const draftPlaceName = ref('')
const selectedWritePlace = ref(null)
const writePlaces = ref(PLACES.slice(0, 6))
const writeSubmitLabel = ref('등록')
const titleLength = computed(() => draftTitle.value.trim().length)
const bodyLength = computed(() => draftBody.value.trim().length)
const passwordLength = computed(() => draftPassword.value.trim().length)
const titleCounter = computed(() => `${Math.min(titleLength.value, 100)}/100`)
const bodyCounter = computed(() => `${Math.min(bodyLength.value, 5000)}/5000`)
const passwordCounter = computed(() => `${Math.min(passwordLength.value, 30)}/30`)

const filtered = computed(() => posts.value)

const communityPostsPage = computed(() => posts.value)

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
  loadPosts()
}

function selectDistrict(d) {
  selectedDistrict.value = d.key
  currentPage.value = 1
  loadPosts()
}

async function openPost(post) {
  try {
    const detail = await getPostDetail(post.id)
    selectedPost.value = mapPostFromApi({ ...detail, content: detail.content || '' })
  } catch (error) {
    selectedPost.value = mapPostFromApi({ ...post, content: post.body || post.content_preview || '' })
  }
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

function formatPostTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function mapPostFromApi(item) {
  return {
    id: item.id,
    category: item.category,
    title: item.title,
    time: formatPostTime(item.created_at),
    views: item.view_count ?? 0,
    placeName: item.location?.title || '장소 미정',
    statusTags: item.status_tag ? [item.status_tag] : [],
    district: item.location?.district || '미지정',
    body: item.content,
    author: '익명',
    raw: item,
  }
}

async function loadPosts() {
  isLoading.value = true
  loadError.value = ''
  try {
    const response = await getPosts({
      q: communitySearchQuery.value || undefined,
      category: selectedCategory.value !== 'all' ? communityCats.value.find((cat) => cat.key === selectedCategory.value)?.label : undefined,
      district: selectedDistrict.value !== 'all' ? selectedDistrict.value : undefined,
      page: currentPage.value,
      size: pageSize,
      sort: 'recent',
    })
    posts.value = (response.data || []).map(mapPostFromApi)
    totalPages.value = response.meta?.total_pages || 1
    totalItems.value = response.meta?.total_items || 0
  } catch (error) {
    loadError.value = error?.message || '게시글을 불러오지 못했습니다.'
    posts.value = []
  } finally {
    isLoading.value = false
  }
}

function goPage(n) {
  currentPage.value = n
  loadPosts()
}

function setCommunitySearchQuery(e) {
  communitySearchQuery.value = e.target.value
  currentPage.value = 1
  loadPosts()
}

function validateDraft() {
  const title = draftTitle.value.trim()
  const body = draftBody.value.trim()
  const password = draftPassword.value.trim()

  if (!title || !body || !selectedWriteCategory.value || !password) {
    return '제목, 내용, 카테고리, 비밀번호를 모두 입력해주세요.'
  }

  if (title.length < 2 || title.length > 100) {
    return '제목은 2~100자 사이로 입력해주세요.'
  }

  if (body.length < 2 || body.length > 5000) {
    return '내용은 2~5000자 사이로 입력해주세요.'
  }

  if (password.length < 4 || password.length > 30) {
    return '비밀번호는 4~30자 사이로 입력해주세요.'
  }

  return ''
}

async function submitPost() {
  const title = draftTitle.value.trim()
  const body = draftBody.value.trim()
  const password = draftPassword.value.trim()
  const categoryKey = selectedWriteCategory.value

  const validationMessage = validateDraft()
  if (validationMessage) {
    alert(validationMessage)
    return
  }

  const categoryLabel = WRITE_CATEGORIES.find((cat) => cat.key === categoryKey)?.label || '현장 제보'
  const statusLabel = selectedStatusTags.value[0] ? WRITE_STATUS_TAGS.find((tag) => tag.key === selectedStatusTags.value[0])?.label : null
  const payload = {
    location_id: selectedWritePlace.value?.id || null,
    category: categoryLabel,
    status_tag: statusLabel,
    title,
    content: body,
    visited_at: null,
    password,
  }

  isSubmitting.value = true
  try {
    if (isEditing.value && editingPostId.value) {
      await updatePost(editingPostId.value, payload)
    } else {
      await createPost(payload)
    }
    await loadPosts()
    backToCommunity()
    currentPage.value = 1
  } catch (error) {
    alert(error?.message || '게시글을 저장하지 못했습니다.')
  } finally {
    isSubmitting.value = false
  }
}

async function handlePostEdit(post) {
  isWrite.value = true
  selectedPost.value = null
  isEditing.value = true
  editingPostId.value = post.id
  writeSubmitLabel.value = '수정 완료'
  const detail = await getPostDetail(post.id)
  selectedWriteCategory.value = getCategoryKey(detail.category)
  selectedStatusTags.value = detail.status_tag ? [WRITE_STATUS_TAGS.find((tag) => tag.label === detail.status_tag)?.key].filter(Boolean) : []
  draftTitle.value = detail.title || ''
  draftBody.value = detail.content || ''
  draftPassword.value = ''
  draftPlaceName.value = detail.location?.title || ''
  selectedWritePlace.value = detail.location ? PLACES.find((place) => place.id === detail.location.id) || null : null
}

async function handlePostDelete(payload) {
  const post = payload?.post || payload
  const password = payload?.password || ''
  if (!password) return
  try {
    await deletePost(post.id, password)
    await loadPosts()
    backToCommunity()
  } catch (error) {
    alert(error?.message || '비밀번호가 올리지 않아 삭제할 수 없습니다.')
  }
}

onMounted(() => {
  loadPosts()
})
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

          <div class="community-write-field">
            <input
              v-model="draftTitle"
              type="text"
              class="community-write-input"
              placeholder="제목을 입력하세요"
              maxlength="100"
            />
            <div class="community-write-counter">{{ titleCounter }}</div>
          </div>

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

          <div class="community-write-field">
            <textarea
              v-model="draftBody"
              class="community-write-textarea"
              placeholder="내용을 입력하세요"
              maxlength="5000"
            />
            <div class="community-write-counter">{{ bodyCounter }}</div>
          </div>

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

          <div class="community-write-field">
            <input
              v-model="draftPassword"
              type="password"
              class="community-write-input"
              placeholder="비밀번호 (글 수정·삭제 시 필요)"
              maxlength="30"
            />
            <div class="community-write-counter">{{ passwordCounter }}</div>
          </div>
          <button class="community-submit-btn" type="button" @click="submitPost" :disabled="isSubmitting">{{ isSubmitting ? '처리 중...' : writeSubmitLabel }}</button>
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

      <div v-if="isLoading" class="empty-results">게시글을 불러오는 중입니다…</div>
      <div v-else-if="loadError" class="empty-results">{{ loadError }}</div>
      <div v-else class="posts-container">
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

        <div v-if="!communityPostsPage.length" class="empty-results">검색 결과가 없어요</div>
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
