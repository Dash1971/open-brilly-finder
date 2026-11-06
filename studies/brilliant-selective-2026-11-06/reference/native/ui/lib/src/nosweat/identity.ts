// The server validates the NIP-19 checksum; these patterns only route public input.
const npubInput = /^(?:nostr:)?(npub1[023456789acdefghjklmnpqrstuvwxyz]{58})$/i;

export const publicIdentitySearch: RegExp =
  /^(?!\s*(?:nostr:)?nsec1)(?:[^\u0000-\u001f\u007f]{2,30}|(?:nostr:)?npub1[023456789acdefghjklmnpqrstuvwxyz]{58})$/iu;

export function npubFromInput(value: string): string | undefined {
  return npubInput.exec(value.trim())?.[1];
}

export function isPrivateNostrInput(value: string): boolean {
  return /^(?:nostr:)?nsec1/i.test(value.trim());
}
