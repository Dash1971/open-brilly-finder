/** Native Lichess catalog; English fallback also supports embedded/test views. */
export function muteText(key: string, fallback: string): string {
  const text =
    typeof i18n !== 'undefined' &&
    (i18n.site as unknown as Record<string, string> | undefined)?.[`mute${key}`];
  return typeof text === 'string' && text ? text : fallback;
}
