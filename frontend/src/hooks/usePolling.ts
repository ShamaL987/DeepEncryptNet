import { useEffect } from 'react'

export const usePolling = (fn: () => void, intervalMs: number) => {
    useEffect(() => {
        fn()
        const id = setInterval(fn, intervalMs)
        return () => clearInterval(id)
    }, [])
}
