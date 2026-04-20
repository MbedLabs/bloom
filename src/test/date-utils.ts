/**
 * Date and time utilities for the Bloom ALM.
 */

export function formatDateTime(
  dateString: string | null | undefined, 
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }
): string {
  if (!dateString) return '-'
  
  try {
    const date = new Date(dateString)
    let preferredTz = localStorage.getItem('bloom-timezone') || 'auto'
    
    // Normalize UTC selection
    if (preferredTz.toLowerCase() === 'utc') {
      preferredTz = 'UTC'
    }
    
    const finalOptions: Intl.DateTimeFormatOptions = { ...options }
    if (preferredTz !== 'auto') {
      finalOptions.timeZone = preferredTz
    }
    
    return new Intl.DateTimeFormat(undefined, finalOptions).format(date)
  } catch (e) {
    console.error('Error formatting date:', e)
    return dateString
  }
}
