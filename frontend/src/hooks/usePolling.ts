import { useEffect, useRef } from 'react';

interface UsePollingOptions {
  enabled: boolean;
  interval: number;
  onPoll: () => void;
}

export const usePolling = ({ enabled, interval, onPoll }: UsePollingOptions) => {
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (enabled) {
      intervalRef.current = setInterval(onPoll, interval);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [enabled, interval, onPoll]);
};
