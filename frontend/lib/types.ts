export type Mode = "understand" | "practise" | "code";
export type Provider = "auto" | "gemini" | "openai" | "anthropic" | "mock";
export type Session = { session_id: string; topic: string; provider: string; updated_at: string };
export type Providers = {
  default_provider: Provider;
  auto_order: string[];
  mock_enabled: boolean;
  configuration_only: boolean;
  providers: { id: Provider; configured: boolean; model: string }[];
};
export type Message = {
  id: string;
  role: string;
  content: string;
  provider: string | null;
  sequence_in_page?: number;
};
export type DocumentInfo = { document_id: string; filename: string; retrieval_status: string };
export type Memory = {
  session_id: string;
  topic: string;
  current_provider: string;
  recap: string | null;
  completed_turns: number;
  learning_state: {
    learning_objective?: string;
    explanation_preference?: string;
    known_concepts?: string[];
    weak_concepts?: string[];
    misconceptions?: string[];
  };
};
export type ChatRequest = {
  session_id: string;
  request_id: string;
  message: string;
  provider: Provider;
  allow_fallback: boolean;
  mode: Mode;
};
export type ChatResult = {
  session_id: string;
  request_id: string;
  provider_used: string;
  provider_requested: string;
  previous_provider: string | null;
  provider_changed: boolean;
  fallback_used: boolean;
  is_mock: boolean;
  response: string;
  turn_no: number;
  route_events: { provider: string; status: string }[];
  context: {
    recent_messages: number;
    source_chunks: string[];
    source_mode: string;
    summary_mode: string;
    context_bytes: number;
    budget_bytes: number;
  };
  usage: {
    input_tokens: number | null;
    output_tokens: number | null;
    estimated_cost: number | null;
  };
};
export type Question = {
  id: string;
  mode: Mode;
  concept: string;
  prompt: string;
  options?: string[];
  hint?: string;
};
export type Feedback = {
  correct: boolean | null;
  verdict: string;
  explanation: string;
  method: string;
  code_executed?: boolean;
  hint: string;
  follow_up: Question;
};
export type Progress = {
  attempts: number;
  concepts: { concept: string; latest_status: string; attempts: number; follow_up: Question }[];
  scope: string;
  mastery_calibrated: boolean;
};
export type Video = {
  id: string;
  video_id: string;
  title: string;
  topic: string;
  start_seconds: number;
  end_seconds: number;
  evidence: string;
  verification: string;
  watch_url: string;
  embed_url: string;
  note: string;
};
export type DataResult = {
  task: string;
  feedback: { verdict: string; issues: string[] };
  calculated_reference: {
    rows: number;
    excluded_rows: number;
    monthly_totals: { month: string; total: string }[];
    category_totals: { category: string; total: string }[];
    total: string;
    method: string;
    missing_months: string;
  };
};

export type DataChoices = {
  date_column: string;
  value_column: string;
  category_column: string;
  grouping: "month" | "region" | "row";
  aggregation: "sum" | "average" | "count";
  chart: "line" | "bar" | "pie";
};

export type SavedDataAnalysis = DataResult & {
  analysis_id: string;
  session_id: string;
  filename: string;
  choices: DataChoices;
  created_at: string;
};
