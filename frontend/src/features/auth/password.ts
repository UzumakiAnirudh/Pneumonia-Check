/** Same rules as the backend (app/schemas/auth.py). */
export function passwordChecks(pw: string) {
  return [
    { ok: pw.length >= 8, label: 'At least 8 characters' },
    { ok: /[A-Za-z]/.test(pw) && /[^A-Za-z]/.test(pw), label: 'Letters plus a number or symbol' },
  ];
}
