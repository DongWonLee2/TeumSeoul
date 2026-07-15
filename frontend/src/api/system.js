import { apiRequest } from './client.js'

export async function getHealth() {
  const response = await apiRequest('/health')
  return response.data
}

export async function getMeta() {
  const response = await apiRequest('/meta')
  return response.data
}
