import { api } from "./api";

export interface CompetencyScore {
  score: number;
  weight: number;
  evidence: string;
  explanation: string;
  interview_feedback_used: boolean;
}

export interface CandidateScorecard {
  competency_scores: Record<string, CompetencyScore>;
  overall_score: number;
  rank: number;
  interview_feedback_score: number | null;
  application_status: string | null;
  low_confidence: boolean;
}

export interface SourceUsed {
  document_id: string;
  type: string;
  sections_read: string[];
}

export interface ScorecardMeta {
  sources_used: SourceUsed[];
  conversation_summary: string;
}

export type ScorecardPayload = Record<string, unknown>;

export interface RankingEntry {
  rank: number;
  anon_id: string;
  overall_score: number;
}

export interface BiasFlag {
  flag_type: string;
  description: string;
  severity: string;
  recommendation: string;
}

export interface ChatResponse {
  answer: string;
  scorecard: ScorecardPayload | null;
  ranking: RankingEntry[];
  bias_flags: BiasFlag[];
  session_id: number;
  updated_conversation_summary?: string;
  sources_used?: SourceUsed[];
}

export interface ChatSession {
  id: number;
  user_id?: number;
  title: string;
  job_id: number | null;
  created_at: string;
  updated_at?: string;
}

export interface ChatMessage {
  id: number;
  session_id?: number;
  role: "user" | "assistant";
  content: string;
  scorecard: ScorecardPayload | null;
  bias_flags: { flags: BiasFlag[] } | null;
  created_at: string;
}

export async function sendMessage(
  question: string,
  job_id: number | null,
  session_id: number,
): Promise<ChatResponse> {
  return api<ChatResponse>("/api/v1/hirelogic/chat", {
    method: "POST",
    data: { question, job_id, session_id },
  });
}

export async function fetchSessions(): Promise<ChatSession[]> {
  return api<ChatSession[]>("/api/v1/hirelogic/sessions");
}

export async function createSession(
  job_id: number | null,
  title: string,
): Promise<ChatSession> {
  return api<ChatSession>("/api/v1/hirelogic/sessions", {
    method: "POST",
    data: { job_id, title },
  });
}

export async function fetchMessages(
  sessionId: number,
): Promise<ChatMessage[]> {
  return api<ChatMessage[]>(
    `/api/v1/hirelogic/sessions/${sessionId}/messages`,
  );
}
