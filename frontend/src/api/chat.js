import { apiRequest } from './client.js'

export async function sendChatMessage(payload, signal) {
  const response = await apiRequest('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  return response.data
}
