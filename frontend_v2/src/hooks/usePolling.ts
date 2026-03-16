import { useEffect, useRef, useState } from "react";

export function usePolling<T>(
    fetcher: () => Promise<T>,
    intervalMs: number
) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const mountedRef = useRef(true);

    useEffect(() => {
        mountedRef.current = true;

        const run = async () => {
            try {
                const result = await fetcher();
                if (!mountedRef.current) return;
                setData(result);
                setError(null);
            } catch (err) {
                if (!mountedRef.current) return;
                setError(err instanceof Error ? err.message : "Failed to fetch");
            } finally {
                if (mountedRef.current) {
                    setLoading(false);
                }
            }
        };

        run();
        const id = setInterval(run, intervalMs);

        return () => {
            mountedRef.current = false;
            clearInterval(id);
        };
    }, [fetcher, intervalMs]);

    return { data, loading, error };
}