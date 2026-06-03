export function getExtraCodes(): string[] {
  try { return JSON.parse(localStorage.getItem('kis_extra_codes') || '[]') }
  catch { return [] }
}

export function saveExtraCodes(arr: string[]) {
  localStorage.setItem('kis_extra_codes', JSON.stringify(arr))
}

export function getOverseasCodes(): string[] {
  try { return JSON.parse(localStorage.getItem('kis_overseas_codes') || '[]') }
  catch { return [] }
}

export function saveOverseasCodes(arr: string[]) {
  localStorage.setItem('kis_overseas_codes', JSON.stringify(arr))
}
