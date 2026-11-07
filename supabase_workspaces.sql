-- SOW IA: add separate Personal and Professional workspaces.
-- Existing memories and messages are preserved in the Personal workspace.
alter table public.sowia_memory_items add column if not exists workspace_id text not null default 'personal';
alter table public.sowia_messages add column if not exists workspace_id text not null default 'personal';
alter table public.sowia_memory_items drop constraint if exists sowia_memory_items_workspace_id_check;
alter table public.sowia_memory_items add constraint sowia_memory_items_workspace_id_check check (workspace_id in ('personal', 'professional'));
alter table public.sowia_messages drop constraint if exists sowia_messages_workspace_id_check;
alter table public.sowia_messages add constraint sowia_messages_workspace_id_check check (workspace_id in ('personal', 'professional'));
create index if not exists sowia_memory_items_user_workspace_created_idx on public.sowia_memory_items (user_id, workspace_id, created_at desc);
create index if not exists sowia_messages_user_workspace_session_idx on public.sowia_messages (user_id, workspace_id, session_id, id desc);
-- Existing RLS policies remain active and continue to enforce user ownership.
