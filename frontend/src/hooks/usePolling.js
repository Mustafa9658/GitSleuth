import { useEffect, useRef } from 'react';

export const usePolling = ({ enabled, interval, onPoll }) => {
  const intervalRef = useRef(null);

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
