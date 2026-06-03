export function fmt(n: number | null | undefined): string {
  if (n == null) return '-'
  return Number(n).toLocaleString('ko-KR')
}

export function fmtF(n: number | null | undefined, d = 2): string {
  if (n == null) return '-'
  return Number(n).toFixed(d)
}

export function fmtVol(n: number): string {
  if (n >= 100000000) return (n / 100000000).toFixed(1) + '억'
  if (n >= 10000) return (n / 10000).toFixed(0) + '만'
  return fmt(n)
}

export function fmtO(n: number | null | undefined): string {
  if (n == null) return '-'
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function fmtVolUS(n: number): string {
  if (n >= 1000000000) return (n / 1000000000).toFixed(1) + 'B'
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(0) + 'K'
  return n.toLocaleString('en-US')
}

export function chgClass(val: number): string {
  if (val > 0) return 'up'
  if (val < 0) return 'down'
  return 'flat'
}

export function signStr(val: number): string {
  return val > 0 ? '+' : ''
}
