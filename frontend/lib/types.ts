export interface Patient {
  patient_id: string;
  mrn: string;
  display_name: string;
  dob: string;
  jurisdiction: string;
  home_region: string;
}

export interface Artifact {
  artifact_id: string;
  patient_id: string;
  artifact_type: string;
  title: string;
  document_date: string;
  source_provider: string;
  status: string;
  s3_uri: string;
  created_at: string;
}

export interface CareThread {
  thread_id: string;
  patient_id: string;
  thread_type: string;
  title: string;
  finding_id: string | null;
  status: string;
  priority: string;
  owner_user_id: string | null;
  due_at: string | null;
  opened_at: string | null;
  closed_at: string | null;
  closure_reason: string | null;
}

export interface ThreadEvent {
  event_id: string;
  event_type: string;
  actor_type: string;
  actor_id: string;
  previous_state: string | null;
  new_state: string | null;
  event_metadata: Record<string, unknown>;
  created_at: string;
}

export interface ThreadEvidence {
  thread_evidence_id: string;
  artifact_id: string;
  chunk_id: string | null;
  relationship_type: string;
  match_score: number;
  match_reason: string;
  approval_status: string;
  linked_at: string;
}

export interface FamilyMember {
  patient_id: string;
  display_name: string;
  mrn: string;
}

export interface FamilyRelationship {
  relationship_id: string;
  patient_id: string;
  related_patient_id: string;
  relationship_type: string;
  notes: string;
}

export interface Family {
  family_id: string;
  family_name: string;
  members: FamilyMember[];
  relationships: FamilyRelationship[];
}

export interface FamilyChatMessage {
  message_id: string;
  family_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface PatientChatMessage {
  message_id: string;
  patient_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ProposedAction {
  action_id: string;
  thread_id: string;
  patient_id: string;
  action_type: string;
  proposed_payload: Record<string, unknown>;
  reason: string;
  confidence: number;
  source_evidence: Record<string, unknown>;
  status: string;
  created_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
}
