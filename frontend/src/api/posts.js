import { apiRequest } from './client.js'

export async function getPostDetail(postId, signal) {
  const response = await apiRequest(`/posts/${postId}`, { signal })
  return response.data
}
