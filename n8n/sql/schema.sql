-- Cordex AI Agent V1 schema
-- Apply this manually against the Postgres database used by n8n credentials.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agent_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  workspace_id text NOT NULL,
  channel text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS agent_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid REFERENCES agent_sessions(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'tool', 'system')),
  content text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_memory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  workspace_id text NOT NULL,
  memory_type text NOT NULL,
  content jsonb NOT NULL,
  importance integer NOT NULL DEFAULT 1 CHECK (importance BETWEEN 1 AND 5),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_tool_calls (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid REFERENCES agent_sessions(id) ON DELETE SET NULL,
  tool_name text NOT NULL,
  input_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL CHECK (status IN ('success', 'pending_approval', 'error', 'blocked')),
  error_message text,
  approval_required boolean NOT NULL DEFAULT false,
  approved_by text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_call_id uuid REFERENCES agent_tool_calls(id) ON DELETE SET NULL,
  requested_by text NOT NULL,
  approved_by text,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'denied', 'expired')),
  reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  decided_at timestamptz
);

CREATE TABLE IF NOT EXISTS agent_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id text NOT NULL,
  filename text NOT NULL,
  source text NOT NULL,
  content_hash text NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'indexed', 'error', 'archived')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES agent_documents(id) ON DELETE CASCADE,
  chunk_index integer NOT NULL,
  content text NOT NULL,
  embedding vector(1536),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS agent_whatsapp_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id text NOT NULL,
  provider_message_id text,
  gym_id text NOT NULL,
  instance text NOT NULL,
  audience text NOT NULL CHECK (audience IN ('internal', 'external')),
  sender_phone text NOT NULL,
  action text NOT NULL DEFAULT 'no_reply' CHECK (action IN ('send_reply', 'create_task', 'handoff', 'no_reply')),
  status text NOT NULL DEFAULT 'received' CHECK (status IN ('received', 'success', 'pending_approval', 'error', 'needs_clarification', 'no_reply', 'blocked')),
  risk_level text NOT NULL DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  input_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (event_id),
  UNIQUE (provider_message_id)
);

CREATE TABLE IF NOT EXISTS agent_user_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  workspace_id text NOT NULL,
  role text NOT NULL CHECK (role IN ('OWNER', 'MANAGER', 'OPERATOR', 'VIEWER')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, workspace_id)
);

CREATE TABLE IF NOT EXISTS agent_tool_policies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_name text NOT NULL,
  action text NOT NULL DEFAULT '*',
  min_role text NOT NULL CHECK (min_role IN ('OWNER', 'MANAGER', 'OPERATOR', 'VIEWER')),
  risk_level text NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  approval_required boolean NOT NULL DEFAULT false,
  enabled boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tool_name, action)
);

CREATE TABLE IF NOT EXISTS agent_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id text NOT NULL,
  title text NOT NULL,
  description text,
  assignee text,
  due_date date,
  priority text NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'completed', 'canceled')),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_user_workspace ON agent_sessions(user_id, workspace_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_session ON agent_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_memory_user_workspace ON agent_memory(user_id, workspace_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_session ON agent_tool_calls(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_approvals_status ON agent_approvals(status, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_documents_workspace ON agent_documents(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_document_chunks_document ON agent_document_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_agent_document_chunks_embedding ON agent_document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_agent_whatsapp_events_gym_status ON agent_whatsapp_events(gym_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_whatsapp_events_sender ON agent_whatsapp_events(sender_phone, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_workspace_status ON agent_tasks(workspace_id, status, due_date);

INSERT INTO agent_tool_policies (tool_name, action, min_role, risk_level, approval_required)
VALUES
  ('web_search', '*', 'VIEWER', 'low', false),
  ('email_assistant', 'search_emails', 'OPERATOR', 'low', false),
  ('email_assistant', 'send_email', 'MANAGER', 'high', true),
  ('calendar_assistant', 'create_event', 'MANAGER', 'high', true),
  ('crm_assistant', '*', 'MANAGER', 'medium', false),
  ('documents_rag', '*', 'VIEWER', 'low', false),
  ('database_query', 'select', 'MANAGER', 'medium', false),
  ('database_query', 'write', 'OWNER', 'critical', true),
  ('task_manager', '*', 'OPERATOR', 'medium', false),
  ('whatsapp_communication', 'draft_message', 'OPERATOR', 'low', false),
  ('whatsapp_communication', 'send_message', 'MANAGER', 'high', true),
  ('whatsapp_communication', 'broadcast', 'OWNER', 'critical', true),
  ('report_generator', '*', 'MANAGER', 'medium', false),
  ('n8n_workflow_manager', 'activate_workflow', 'OWNER', 'critical', true)
ON CONFLICT (tool_name, action) DO NOTHING;
