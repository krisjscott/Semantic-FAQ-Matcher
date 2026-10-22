import { z } from 'zod';
import { evaluationSchema, faqSchema, matchSchema, metadataSchema } from '../types';

async function request<T>(path: string, schema: z.ZodType<T>, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body), signal,
  });
  if (!response.ok) {
    throw new Error(response.status === 422
      ? 'The request or dataset is invalid. Check the API response at /docs for details.'
      : `The API returned ${response.status}. Check that the backend is running, then try again.`);
  }
  const data: unknown = await response.json();
  return schema.parse(data);
}

export const api = {
  metadata: (signal?: AbortSignal) => request('/metadata', metadataSchema, undefined, signal),
  faqs: (signal?: AbortSignal) => request('/faqs', z.array(faqSchema), undefined, signal),
  match: (query: string, threshold: number, signal?: AbortSignal) => request('/match', matchSchema, { query, threshold }, signal),
  evaluate: (threshold: number, signal?: AbortSignal) => request('/evaluate', evaluationSchema, { threshold }, signal),
};

export function errorMessage(error: unknown): string {
  return error instanceof TypeError ? 'Cannot reach the API. Start the backend on port 8000 and try again.'
    : error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}

export function downloadJSON(data: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
