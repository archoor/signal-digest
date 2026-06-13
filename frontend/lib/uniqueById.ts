/** 按 id 去重，避免 API 重复行导致 React key 冲突。 */
export function uniqueById<T extends { id: number }>(items: T[]): T[] {
  const map = new Map<number, T>();
  for (const item of items) {
    map.set(item.id, item);
  }
  return [...map.values()];
}

/** 评论重点条目去重。 */
export function uniqueHighlightItems<
  T extends { review: { id: number } },
>(items: T[]): T[] {
  const map = new Map<number, T>();
  for (const item of items) {
    map.set(item.review.id, item);
  }
  return [...map.values()];
}
