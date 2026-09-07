/* Mirrors the JSON produced by authentix/report.py */

export type Band = "Credible" | "Guarded" | "Suspicious" | "Untrusted" | "Unknown";
export type SeverityLabel = "Info" | "Low" | "Medium" | "High";

export interface WhoWhen {
  when: string | null;
  by: string | null;
  tool: string | null;
}

export interface Finding {
  code: string;
  severity: 1 | 2 | 3 | 4;
  severity_label: SeverityLabel;
  category: string;
  title: string;
  detail: string;
  evidence: Record<string, unknown>;
}

export interface TimelineEvent {
  when: string | null;
  label: string;
  source: string;
  confidence: "high" | "medium" | "low";
  note: string | null;
}

export interface Signature {
  index: number;
  byte_range: number[];
  covered_bytes: number;
  bytes_after_signature: number;
  covers_whole_file: boolean;
  superseded_by_later_revision: boolean;
  sub_filter: string | null;
  filter: string | null;
  name: string | null;
  reason: string | null;
  location: string | null;
  contact_info: string | null;
  signing_time: string | null;
  is_certification: boolean;
  docmdp_permission: number | null;
  signer_subject?: string | null;
  signer_issuer?: string | null;
  cert_not_before?: string | null;
  cert_not_after?: string | null;
  self_signed?: boolean;
  cert_chain_length?: number;
  integrity: "structure-intact" | "superseded" | "modified-after-signing";
  pkcs7?: string;
}

export interface GraphEdge {
  id: string;
  a: string;
  b: string;
  relation: string;
  status: "consistent" | "weak" | "contradiction";
  kappa: number;
  expected: string;
  observed: string;
}

export interface ConsistencyGraph {
  nodes: string[];
  edges: GraphEdge[];
  edge_count: number;
  contradiction_count: number;
  weak_count: number;
  contradiction_density: number;
  mean_kappa: number;
}

export interface Ewdca {
  credibility_score: number | null;
  band: Band;
  risk: number | null;
  score_capped_at: number | null;
  cap_reason: string | null;
  components: Record<string, number>;
  weights: Record<string, number>;
  signed: boolean;
  primary_drivers: string[];
  risk_factors: { title: string; severity: SeverityLabel; category: string; detail: string }[];
}

export interface Report {
  product: string;
  version: string;
  analyzed_at: string;
  file: {
    name: string;
    size_bytes: number;
    sha256: string;
    md5: string;
    format: string;
    format_detail: string;
  };
  summary: {
    credibility_score: number | null;
    band: Band;
    verdict: string;
    title: string | null;
    created: WhoWhen;
    last_modified: WhoWhen;
    revisions: number;
    signed: boolean;
    signature_status: string;
    tampering_detected: boolean;
    tampering_count: number;
    findings_total: number;
    origin_known: boolean;
  };
  origin: {
    author: string | null;
    last_modified_by: string | null;
    creator_application: string | null;
    producer: string | null;
    creator_tool_xmp: string | null;
    creation_date: string | null;
    modification_date: string | null;
    tool_kind: "application" | "generator" | "manipulator" | null;
    library: string | null;
    toolchain_inference: string;
  };
  timeline: TimelineEvent[];
  findings: Finding[];
  signatures: Signature[];
  consistency_graph: ConsistencyGraph;
  ewdca: Ewdca;
  evidence: Record<string, unknown>;
  errors: { stage: string; error: string }[];
}
