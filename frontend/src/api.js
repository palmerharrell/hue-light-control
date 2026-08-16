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
    throw new Error(parsed.detail ?? `Request failed (${res.status})`)
  }
  return res.json()
}

export function putJson(url, body) {
  return fetchJson(url, { method: 'PUT', body })
}

export function postJson(url, body) {
  return fetchJson(url, { method: 'POST', body })
}
