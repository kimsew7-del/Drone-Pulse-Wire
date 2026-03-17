'use client';

import { useState, useEffect, useCallback } from 'react';

/**
 * Hook for localStorage-backed state.
 * Useful for persisting liked/saved article IDs across sessions.
 */
export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(initialValue);

  // Read from localStorage on mount
  useEffect(() => {
    try {
      const item = localStorage.getItem(key);
      if (item !== null) {
        setStoredValue(JSON.parse(item) as T);
      }
    } catch {
      // If parsing fails, keep the initial value
    }
  }, [key]);

  // Setter that also writes to localStorage
  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const nextValue = value instanceof Function ? value(prev) : value;
        try {
          localStorage.setItem(key, JSON.stringify(nextValue));
        } catch {
          // localStorage might be full or unavailable
        }
        return nextValue;
      });
    },
    [key]
  );

  // Remove the key from localStorage
  const removeValue = useCallback(() => {
    try {
      localStorage.removeItem(key);
    } catch {
      // Ignore errors
    }
    setStoredValue(initialValue);
  }, [key, initialValue]);

  return [storedValue, setValue, removeValue] as const;
}
