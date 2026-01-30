
export interface DomainAnalysis {
  domain: string;
  rating: number;
  observation: string;
  evidence: string;
}

export interface ReportData {
  proficiency_level: string;
  ceiling_phase: string;
  ceiling_analysis: string;
  domain_analyses: DomainAnalysis[];
  starting_module: string;
  optimization_strategy: string;
}

export interface AssessmentData {
  session_id: string;
  timestamp: string;
  report: ReportData;
  verbal_summary: string;
  conversation_length: number;
}
