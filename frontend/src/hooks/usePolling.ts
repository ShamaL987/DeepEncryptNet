import { DependencyList, useEffect } from 'react'

export const usePolling = (fn: () => void | Promise<void>, intervalMs: number, deps: DependencyList = []) => {
  useEffect(() => {
    fn()
    const id = setInterval(() => {
      void fn()
    }, intervalMs)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
