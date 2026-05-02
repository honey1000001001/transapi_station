import dayjs from 'dayjs';
import { DATE_FORMAT } from './constants';

// Number formatting with commas
export function formatNumber(num: number | undefined | null): string {
  if (num === undefined || num === null) return '0';
  return num.toLocaleString('zh-CN');
}

// Currency formatting with ¥ prefix
export function formatCost(cost: number | undefined | null): string {
  if (cost === undefined || cost === null) return '¥0.00';
  return `¥${cost.toFixed(4)}`;
}

export function formatCostShort(cost: number | undefined | null): string {
  if (cost === undefined || cost === null) return '¥0';
  if (cost >= 1) return `¥${cost.toFixed(2)}`;
  return `¥${cost.toFixed(4)}`;
}

// Date formatting
export function formatDate(date: string | Date | undefined | null): string {
  if (!date) return '-';
  return dayjs(date).format(DATE_FORMAT);
}

export function formatDateShort(date: string | Date | undefined | null): string {
  if (!date) return '-';
  return dayjs(date).format('YYYY-MM-DD');
}

// Token display: prompt / completion / total
export function formatTokenDisplay(
  prompt: number | undefined | null,
  completion: number | undefined | null
): string {
  const p = prompt ?? 0;
  const c = completion ?? 0;
  return `${formatNumber(p)} / ${formatNumber(c)} / ${formatNumber(p + c)}`;
}

// Latency formatting
export function formatLatency(ms: number | undefined | null): string {
  if (ms === undefined || ms === null) return '-';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

// Relative time
export function formatRelativeTime(date: string | Date): string {
  const now = dayjs();
  const target = dayjs(date);
  const diffMin = now.diff(target, 'minute');
  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = now.diff(target, 'hour');
  if (diffHour < 24) return `${diffHour}小时前`;
  const diffDay = now.diff(target, 'day');
  if (diffDay < 30) return `${diffDay}天前`;
  return formatDate(date);
}

// Key prefix display
export function formatKeyPrefix(prefix: string): string {
  if (!prefix) return '-';
  return `${prefix}****`;
}
