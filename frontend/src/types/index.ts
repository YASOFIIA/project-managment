export interface User {
  id: number;
  login: string;
  email: string;
  created_at: string;
}

export interface Document {
  id: number;
  project_id: number;
  filename: string;
  file_size_bytes: number;
  content_type: string;
  created_at: string;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  total_size_bytes: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends Project {
  documents: Document[];
}

export type Role = 'owner' | 'participant';

export interface ProjectMember {
  id: number;
  project_id: number;
  user_id: number;
  login: string;
  role: Role;
  created_at: string;
}

// Response of join and accept invitation endpoints
export interface MembershipResponse {
  id: number;
  project_id: number;
  user_id: number;
  role: Role;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface InvitationResponse {
  message: string;
  email: string;
  expires_in_hours: number;
}

export interface PendingInvitation {
  id: number;
  project_id: number;
  project_name: string;
  email: string;
  created_at: string;
  expires_at: string;
}
