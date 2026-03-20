import { useCallback, useEffect, useRef, useState } from "react";

export function usePolling<T>(
    fetcher: () => Promise<T>,
    intervalMs: number
) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const mountedRef = useRef(false);
    const fetcherRef = useRef(fetcher);
    const initializedFetcherRef = useRef(false);

    const run = useCallback(async () => {
        setLoading(true);

        try {
            const result = await fetcherRef.current();
            if (!mountedRef.current) return null;

            setData(result);
            setError(null);
            return result;
        } catch (err) {
            if (!mountedRef.current) return null;

            setError(err instanceof Error ? err.message : "Failed to fetch");
            return null;
        } finally {
            if (mountedRef.current) {
                setLoading(false);
            }
        }
    }, []);

    useEffect(() => {
        mountedRef.current = true;

        run();
        const id = setInterval(run, intervalMs);

        return () => {
            mountedRef.current = false;
            clearInterval(id);
        };
    }, [run, intervalMs]);

    useEffect(() => {
        fetcherRef.current = fetcher;

        if (!initializedFetcherRef.current) {
            initializedFetcherRef.current = true;
            return;
        }

        run();
    }, [fetcher, run]);

    return { data, loading, error, refetch: run };
}