import { writable } from 'svelte/store'

export const registry = writable(null)
export const subjects = writable([])
export const currentReport = writable(null)
