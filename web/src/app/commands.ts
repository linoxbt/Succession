/** Values pasted into a shell must remain one literal argument. */
export function shellArgument(value: string): string {
  const quote = (s: string) => `'${s.replace(/'/g, `'"'"'`)}'`;
  return value.startsWith("~/") ? `"$HOME"/${quote(value.slice(2))}` : quote(value);
}

export function usdcMinorUnits(value: string): bigint | null {
  if (!/^\d{1,30}(\.\d{1,6})?$/.test(value.trim())) return null;
  const [whole = "0", fraction = ""] = value.trim().split(".");
  const minor = BigInt(whole) * 1_000_000n + BigInt(fraction.padEnd(6, "0"));
  return minor > 0n ? minor : null;
}
