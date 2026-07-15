import { apiRequest } from './client.js'

export async function getSituationalRecommendations(payload, signal) {
  return apiRequest('/recommend/situational', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
}
