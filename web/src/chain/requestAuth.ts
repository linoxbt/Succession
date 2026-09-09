/** Canonical request authorization, shared byte-for-byte with succession.auth. */
export function keyRequestMessage(listingId: string, chainId: number, contract: string,
  timestamp: number, nonce: string): string {
  if (!/^[A-Za-z0-9_.-]{1,32}$/.test(listingId)) throw new Error('Invalid listing ID');
  return 'Succession/request/v2\n' + JSON.stringify({
    body_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    chain_id: chainId, contract: contract.toLowerCase(), listing_id: listingId,
    method: 'GET', nonce, path: `/api/listing/${listingId}/key`, timestamp,
  });
}
