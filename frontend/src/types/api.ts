export type PersonSummary = {
  person_id: string
  full_name: string
  email?: string | null
  group?: string | null
  time_availability?: string | null
}

export type PersonSearchResponse = {
  items: PersonSummary[]
}

export type DueDiligenceSubjectSummary = {
  subject_id: string
  subject_name: string
  subject_label: string
  last_launch_at?: string | null
  investigation_count: number
}

export type DueDiligenceSubjectSearchResponse = {
  items: DueDiligenceSubjectSummary[]
}

export type InvestigationRunSummary = {
  run_id: string
  subject_id: string
  subject_name: string
  subject_label: string
  status?: string | null
  run_kind?: string | null
  start_mode?: string | null
  started_at?: string | null
  completed_at?: string | null
  selected_sources: string[]
  opensanctions_dataset?: string | null
  error_count: number
  dossier_generated_at?: string | null
  report_generated_at?: string | null
}

export type InvestigationSearchResponse = {
  items: InvestigationRunSummary[]
}

export type ConversationSummary = {
  id: string
  topic: string
  description?: string | null
  is_open: boolean
  allow_comment_submission: boolean
  allow_viz: boolean
  moderation_required: boolean
  created_at?: string | null
  comments?: number | null
  participants?: number | null
}
