<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  post: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['back', 'edit', 'delete'])

const passwordPromptOpen = ref(false)
const passwordInput = ref('')
const hasPasswordError = ref(false)
const passwordError = ref('')

const detailPost = computed(() => ({
  category: props.post.category || '카테고리',
  placeName: props.post.placeName || '장소 미정',
  title: props.post.title || '제목 없음',
  author: props.post.author || '익명',
  time: props.post.time || '',
  views: props.post.views ?? 0,
  body: props.post.body || '아직 작성된 내용이 없습니다.',
  statusTags: props.post.statusTags || [],
}))

function handleBack() {
  emit('back')
}

function handleEdit() {
  emit('edit', props.post)
}

function handleDelete() {
  passwordPromptOpen.value = true
  passwordInput.value = ''
  hasPasswordError.value = false
  passwordError.value = ''
}

function cancelPasswordPrompt() {
  passwordPromptOpen.value = false
  passwordInput.value = ''
  hasPasswordError.value = false
  passwordError.value = ''
}

function confirmPasswordPrompt() {
  const password = passwordInput.value.trim()
  if (!password) {
    hasPasswordError.value = true
    passwordError.value = '비밀번호를 입력해주세요.'
    return
  }

  hasPasswordError.value = false
  passwordPromptOpen.value = false
  passwordInput.value = ''
  emit('delete', { post: props.post, password })
}
</script>

<template>
  <div class="post-detail-screen">
    <div class="post-detail-header">
      <button class="post-detail-back" type="button" @click="handleBack">← 커뮤니티로 돌아가기</button>
    </div>

    <div class="post-detail-tags-row">
      <span class="post-detail-category">{{ detailPost.category }}</span>
      <template v-if="detailPost.statusTags.length">
        <span v-for="tag in detailPost.statusTags" :key="tag" class="post-detail-status-tag">{{ tag }}</span>
      </template>
      <span class="post-detail-place">📍 {{ detailPost.placeName }}</span>
    </div>

    <h1 class="post-detail-title">{{ detailPost.title }}</h1>

    <div class="post-detail-meta-row">
      <div class="post-detail-meta">
        <span>{{ detailPost.author }}</span>
        <span>{{ detailPost.time }}</span>
        <span>조회 {{ detailPost.views }}</span>
      </div>
      <div class="post-detail-actions post-detail-actions-inline">
        <button class="post-detail-action" type="button" @click="handleEdit">수정</button>
        <button class="post-detail-action" type="button" @click="handleDelete">삭제</button>
      </div>
    </div>

    <p class="post-detail-body">{{ detailPost.body }}</p>
  </div>

  <div v-if="passwordPromptOpen" class="password-prompt-backdrop">
    <div class="password-prompt-card">
      <div class="password-prompt-title">비밀번호를 확인해주세요</div>
      <input
        v-model="passwordInput"
        type="password"
        class="password-prompt-input"
        placeholder="비밀번호를 입력하세요"
      />
      <div v-if="hasPasswordError" class="password-prompt-error">{{ passwordError }}</div>
      <div class="password-prompt-actions">
        <button class="password-prompt-cancel" type="button" @click="cancelPasswordPrompt">취소</button>
        <button class="password-prompt-confirm" type="button" @click="confirmPasswordPrompt">확인</button>
      </div>
    </div>
  </div>
</template>
