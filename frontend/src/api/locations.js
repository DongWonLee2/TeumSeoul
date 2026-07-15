import { apiRequest } from './client.js'

export async function getLocationDetail(locationId) {
  const response = await apiRequest(`/locations/${locationId}`)
  return response.data
}
