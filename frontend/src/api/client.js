const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status, code) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: 'application/json', ...options.headers },
    ...options,
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new ApiError(
      errorBody.detail || '서버 요청에 실패했습니다.',
      response.status,
      errorBody.code,
    )
  }

  if (response.status === 204) return null
  return response.json()
}
