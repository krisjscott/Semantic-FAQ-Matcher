import { z } from 'zod';

export const faqSchema = z.object({
  faq_id: z.string(), category: z.string(), question: z.string(), answer: z.string(),
});
export type FAQ = z.infer<typeof faqSchema>;
const datasetSchema = z.object({
  key: z.string(), name: z.string(), filename: z.string(), labeled: z.boolean(),
  available: z.boolean(), count: z.number(),
});
export const metadataSchema = z.object({
  model: z.string(), faq_count: z.number(),
  categories: z.array(z.object({ name: z.string(), count: z.number() })),
  default_threshold: z.number(), semantic_weight: z.number(), keyword_weight: z.number(),
  dataset_sha256: z.string(), datasets: z.array(datasetSchema),
});
export type Metadata = z.infer<typeof metadataSchema>;
export const matchSchema = z.object({
  status: z.enum(['Match found', 'No suitable match', 'Invalid query']),
  faq_id: z.string().nullable(), matched_question: z.string().nullable(),
  answer: z.string(), category: z.string().nullable(), similarity: z.number(),
  threshold: z.number(), elapsed_ms: z.number(),
  top_matches: z.array(faqSchema.extend({
    score: z.number(), semantic_similarity: z.number(), keyword_overlap: z.number(),
  })),
});
export type Match = z.infer<typeof matchSchema>;
export const evaluationSchema = z.object({
  threshold: z.number(), model: z.string(), measured_at: z.string(),
  duplicate_query_rows: z.number(), test_sha256: z.record(z.string(), z.string()),
  datasets: z.array(datasetSchema.extend({
    valid_count: z.number(), invalid_count: z.number(),
    top1_accuracy: z.number().nullable(), top3_accuracy: z.number().nullable(),
    accepted_accuracy: z.number().nullable(), rejection_rate: z.number().nullable(),
    false_accepts: z.number().nullable(),
  })),
  rows: z.array(z.object({
    dataset: z.string(), query: z.string(), expected_faq_id: z.string().nullable(),
    valid_label: z.boolean(), candidates: z.array(z.string()), score: z.number(),
    predicted_faq_id: z.string().nullable(), top1_correct: z.boolean().nullable(),
    top3_correct: z.boolean().nullable(), correct: z.boolean().nullable(),
  })),
  threshold_sweep: z.array(z.object({
    threshold: z.number(), correct_match_rate: z.number().nullable(),
    rejection_rate: z.number().nullable(),
  })),
});
export type Evaluation = z.infer<typeof evaluationSchema>;
export type Remote<T> =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'success'; data: T }
  | { kind: 'error'; message: string };
