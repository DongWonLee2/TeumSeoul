import { apiRequest } from './client.js'

function buildQuery(params) {
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === 'all') return
    query.set(key, String(value))
  })

  return query.toString()
}

export async function getLocations(params = {}, signal) {
  const query = buildQuery(params)
  return apiRequest(`/locations${query ? `?${query}` : ''}`, { signal })
}

export async function getMapLocations(params, signal) {
  const query = buildQuery(params)
  return apiRequest(`/map/locations?${query}`, { signal })
}

export async function getLocationDetail(locationId, signal) {
  const response = await apiRequest(`/locations/${locationId}`, { signal })
  return response.data
}
