const BASE_URL = 'http://localhost:8000'

export async function getRegistry() {
  const res = await fetch(`${BASE_URL}/registry`)
  if (!res.ok) throw new Error(`getRegistry failed: ${res.status}`)
  return res.json()
}

export async function getSubjects() {
  const res = await fetch(`${BASE_URL}/subjects`)
  if (!res.ok) throw new Error(`getSubjects failed: ${res.status}`)
  return res.json()
}

export async function postTimegraph(params) {
  const res = await fetch(`${BASE_URL}/timegraph`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) throw new Error(`postTimegraph failed: ${res.status}`)
  return res.json()
}
