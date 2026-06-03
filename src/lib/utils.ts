import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Convert UTC timestamp to IST (Indian Standard Time) format
 * @param timestamp - ISO string or Date object
 * @returns Formatted IST string (MMM DD, YYYY at HH:mm:ss IST)
 */
export function formatToIST(timestamp: string | Date): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  
  // Format using toLocaleString with Asia/Kolkata timezone
  const options: Intl.DateTimeFormatOptions = {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  };
  
  const formatted = date.toLocaleString('en-US', options);
  return formatted + ' IST';
}

/**
 * Get current time in IST format
 * @returns Current IST time string
 */
export function getCurrentIST(): string {
  return formatToIST(new Date());
}
