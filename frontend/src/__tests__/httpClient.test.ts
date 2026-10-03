import { createHttpClient } from '@/api/httpClient';
import { ApiError } from '@/api/types';

function respond(status: number, body: string, type: string) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
    new Response(body, { status, headers: { 'content-type': type } }),
  );
}

describe('httpClient without a backend', () => {
  afterEach(() => vi.restoreAllMocks());

  it('explains a 405 HTML page (static host with no API) instead of "Request failed"', async () => {
    respond(405, '<html>Method Not Allowed</html>', 'text/html');
    const err = await createHttpClient('')
      .register({ name: 'A', email: 'a@b.co', password: 'pass-word-1' })
      .catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).message).toMatch(/analysis server is not connected/i);
  });

  it('treats an HTML 200 for an API call as a missing backend', async () => {
    respond(200, '<!doctype html><html></html>', 'text/html');
    await expect(createHttpClient('').health()).rejects.toThrow(/not connected/i);
  });

  it('keeps real API errors from the backend', async () => {
    respond(
      409,
      JSON.stringify({
        detail: { code: 'email_taken', message: 'An account with this email already exists.' },
      }),
      'application/json',
    );
    await expect(
      createHttpClient('').register({ name: 'A', email: 'a@b.co', password: 'pass-word-1' }),
    ).rejects.toThrow('An account with this email already exists.');
  });
});
