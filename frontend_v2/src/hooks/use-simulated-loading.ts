import { useState, useEffect } from "react";

/** Simulates a loading delay (for demo/mock purposes). Replace with real data fetching state. */
export function useSimulatedLoading(delayMs = 1200) {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), delayMs);
    return () => clearTimeout(timer);
  }, [delayMs]);

  return isLoading;
}
