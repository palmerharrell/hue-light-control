// FastAPI's `detail` is usually a string, but on a 422 it's a list of
// pydantic error objects ({msg, loc, ...}) — join those into readable text
// instead of letting `new Error()` stringify the array as "[object Object]".
function formatDetail(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((e) => e.msg ?? JSON.stringify(e)).join('; ')
  return undefined
}

export async function fetchJson(url, options = {}) {
  const { method, body } = options
  const fetchOptions = { method }
  if (body !== undefined) {
    fetchOptions.headers = { 'Content-Type': 'application/json' }
    fetchOptions.body = JSON.stringify(body)
  }

  const res = await fetch(url, fetchOptions)
  if (!res.ok) {
    const parsed = await res.json().catch(() => ({}))
    throw new Error(formatDetail(parsed.detail) ?? `Request failed (${res.status})`)
  }
  return res.json()
}

export function putJson(url, body) {
  return fetchJson(url, { method: 'PUT', body })
}

export function postJson(url, body) {
  return fetchJson(url, { method: 'POST', body })
}

export function deleteJson(url) {
  return fetchJson(url, { method: 'DELETE' })
}
