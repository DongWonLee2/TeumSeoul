import { apiRequest } from './client.js'

export async function getPosts(params = {}) {
  const query = new URLSearchParams()

  if (params.q) query.set('q', params.q)
  if (params.category) query.set('category', params.category)
  if (params.statusTag) query.set('status_tag', params.statusTag)
  if (params.locationId) query.set('location_id', String(params.locationId))
  if (params.district) query.set('district', params.district)
  if (params.sort) query.set('sort', params.sort)
  if (params.page) query.set('page', String(params.page))
  if (params.size) query.set('size', String(params.size))

  const queryString = query.toString()
  const response = await apiRequest(queryString ? `/posts?${queryString}` : '/posts')
  return response
}

export async function getPostDetail(postId) {
  const response = await apiRequest(`/posts/${postId}`)
  return response.data
}

export async function createPost(payload) {
  const response = await apiRequest('/posts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

export async function updatePost(postId, payload) {
  const response = await apiRequest(`/posts/${postId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

export async function deletePost(postId, password) {
  await apiRequest(`/posts/${postId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
}
