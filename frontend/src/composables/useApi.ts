import {
  onScopeDispose,
  ref,
  shallowRef,
  toValue,
  watch,
  type MaybeRefOrGetter,
  type Ref,
  type ShallowRef,
} from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export interface ApiOptions<T> {
  /** Keep re-fetching in the background every `pollMs` while this returns true. */
  pollWhile?: (data: T) => boolean
  pollMs?: number
}

export interface ApiState<T> {
  data: ShallowRef<T | null>
  /** True only while there is nothing to show yet — background polls don't flip it. */
  loading: Ref<boolean>
  error: Ref<string | null>
  reload: () => Promise<void>
}

export function useApi<T>(
  path: MaybeRefOrGetter<string>,
  options: ApiOptions<T> = {},
): ApiState<T> {
  const pollMs = options.pollMs ?? 4000
  const data = shallowRef<T | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let controller: AbortController | null = null
  let timer: ReturnType<typeof setTimeout> | undefined

  async function load(background = false): Promise<void> {
    clearTimeout(timer)
    controller?.abort()
    const ctrl = (controller = new AbortController())
    if (!background) {
      loading.value = true
      error.value = null
    }
    try {
      const res = await fetch(`${API_BASE}${toValue(path)}`, { signal: ctrl.signal })
      if (!res.ok) throw new Error(await errorMessage(res))
      const body = (await res.json()) as T
      data.value = body
      error.value = null
      if (options.pollWhile?.(body)) timer = setTimeout(() => load(true), pollMs)
    } catch (err) {
      if (ctrl.signal.aborted) return
      if (background && data.value) {
        // A failed background poll keeps showing what we have and tries again later
        timer = setTimeout(() => load(true), pollMs * 2)
        return
      }
      error.value = describe(err)
    } finally {
      if (controller === ctrl) loading.value = false
    }
  }

  watch(
    () => toValue(path),
    () => {
      data.value = null
      void load()
    },
    { immediate: true },
  )

  onScopeDispose(() => {
    clearTimeout(timer)
    controller?.abort()
  })

  return { data, loading, error, reload: () => load() }
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body: unknown = await res.json()
    if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
    // non-JSON error body
  }
  return `Request failed (${res.status})`
}

function describe(err: unknown): string {
  if (err instanceof TypeError) return "Can't reach the Free Stop API. Is the backend running?"
  return err instanceof Error ? err.message : 'Something went wrong'
}
