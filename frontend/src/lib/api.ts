/**
 * FactLoom API Client
 * Connects frontend to the FastAPI backend endpoints
 */

export interface FactSummary {
  id: string;
  entity: string;
  metric: string;
  scope: string | null;
  period: string | null;
  measurement_type: string | null;
  definition: string | null;
  observation_count: number;
}

export interface Observation {
  id: string;
  fact_id: string;
  document_id: string;
  document_filename?: string;
  page_number: number;
  value: string;
  unit: string | null;
  quote_span: string | null;
  bbox: string | null; // JSON string [x0, y0, x1, y1]
  doc_vintage_date: string | null;
  confidence: number | null;
  created_at?: string;
}

export interface Relationship {
  id: string;
  observation_a_id: string;
  observation_b_id: string;
  relationship_type?: 'SAME_AS' | 'CONTRADICTS' | 'SUPERSEDES' | 'RECONCILED_BY' | 'UNRESOLVED' | string;
  type?: 'SAME_AS' | 'CONTRADICTS' | 'SUPERSEDES' | 'RECONCILED_BY' | 'UNRESOLVED' | string;
  dimension: string;
  justification: string;
  verified_bool: number | boolean;
  value_a?: string;
  unit_a?: string | null;
  quote_a?: string | null;
  value_b?: string;
  unit_b?: string | null;
  quote_b?: string | null;
  doc_a?: string;
  doc_b?: string;
}

export interface FactDetail {
  fact: FactSummary;
  observations: Observation[];
  relationships: Relationship[];
}

export interface Citation {
  token: string;
  observation_id: string;
  fact_id?: string;
  entity?: string;
  metric?: string;
  period?: string;
  value?: string;
  unit?: string | null;
  document_id?: string;
  document_filename?: string;
  page_number?: number;
  quote_span?: string | null;
  bbox?: number[] | null;
}

export interface AskResponse {
  question: string;
  answer: string;
  is_ambiguous: boolean;
  facts_retrieved: FactSummary[];
  observations_cited: Observation[];
  relationships_used: Relationship[];
  citations: Citation[];
}

export interface DocumentInfo {
  id: string;
  filename: string;
  doc_type_guess: string | null;
  uploaded_at: string;
  page_count: number;
  parsed_pages: number;
}

const API_BASE = '/api';

export async function fetchFacts(params?: { entity?: string; metric?: string; period?: string }): Promise<FactSummary[]> {
  const query = new URLSearchParams();
  if (params?.entity) query.set('entity', params.entity);
  if (params?.metric) query.set('metric', params.metric);
  if (params?.period) query.set('period', params.period);

  const url = `${API_BASE}/facts${query.toString() ? `?${query.toString()}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch facts: ${res.statusText}`);
  return res.json();
}

export async function fetchFactDetail(factId: string): Promise<FactDetail> {
  const res = await fetch(`${API_BASE}/facts/${encodeURIComponent(factId)}`);
  if (!res.ok) throw new Error(`Failed to fetch fact details: ${res.statusText}`);
  return res.json();
}

export async function fetchRelationships(): Promise<Relationship[]> {
  const res = await fetch(`${API_BASE}/relationships`);
  if (!res.ok) throw new Error(`Failed to fetch relationships: ${res.statusText}`);
  return res.json();
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`Question answering failed: ${res.statusText}`);
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error(`Failed to fetch documents: ${res.statusText}`);
  return res.json();
}

export async function uploadDocumentFile(file: File): Promise<{ document_id: string; pages_parsed: number }> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/documents`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}
