import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Convert UTC timestamp to IST (Indian Standard Time) format
 * @param timestamp - ISO string or Date object
 * @returns Formatted IST string (YYYY-MM-DD HH:mm:ss IST)
 */
export function formatToIST(timestamp: string | Date): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  // IST is UTC+5:30
  const istOffset = 5.5 * 60 * 60 * 1000; // 5.5 hours in milliseconds
  const istDate = new Date(date.getTime() + istOffset);
  return istDate.toISOString().replace("T", " ").substring(0, 19) + " IST";
}

/**
 * Get current time in IST format
 * @returns Current IST time string
 */
export function getCurrentIST(): string {
  return formatToIST(new Date());
}
