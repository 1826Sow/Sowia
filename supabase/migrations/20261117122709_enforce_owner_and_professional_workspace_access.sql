-- Enforce owner isolation and Premium authorization in the same permissive policy.
-- PostgreSQL combines permissive policies with OR, so separate owner-only and
-- workspace-only policies would unintentionally bypass the Premium restriction.

DROP POLICY IF EXISTS "Require Premium for Professional messages" ON public.sowia_messages;
DROP POLICY IF EXISTS "Restrict SOW IA messages to owner" ON public.sowia_messages;
DROP POLICY IF EXISTS "Require Premium for Professional memories" ON public.sowia_memory_items;
DROP POLICY IF EXISTS "Restrict SOW IA memories to owner" ON public.sowia_memory_items;

DROP POLICY IF EXISTS messages_select_own ON public.sowia_messages;
CREATE POLICY messages_select_own ON public.sowia_messages
FOR SELECT TO authenticated
USING (user_id = (SELECT auth.uid()) AND (workspace_id = 'personal' OR public.sowia_has_professional_access()));

DROP POLICY IF EXISTS messages_insert_own ON public.sowia_messages;
CREATE POLICY messages_insert_own ON public.sowia_messages
FOR INSERT TO authenticated
WITH CHECK (user_id = (SELECT auth.uid()) AND (workspace_id = 'personal' OR public.sowia_has_professional_access()));

DROP POLICY IF EXISTS messages_update_own ON public.sowia_messages;
CREATE POLICY messages_update_own ON public.sowia_messages
FOR UPDATE TO authenticated
USING (user_id = (SELECT auth.uid()) AND (workspace_id = 'personal' OR public.sowia_has_professional_access()))
WITH CHECK (user_id = (SELECT auth.uid()) AND (workspace_id = 'personal' OR public.sowia_has_professional_access()));

DROP POLICY IF EXISTS messages_delete_own ON public.sowia_messages;
CREATE POLICY messages_delete_own ON public.sowia_messages
FOR DELETE TO authenticated
USING (user_id = (SELECT auth.uid()) AND (workspace_id = 'personal' OR public.sowia_has_professional_access()));

DROP POLICY IF EXISTS memory_select_own ON public.sowia_memory_items;
CREATE POLICY memory_select_own ON public.sowia_memory_items
FOR SELECT TO authenticated
USING (user_id = (SELECT auth.uid()) AND (workspace_id = 'personal' OR public.sowia_has_professional_access()));

DROP POLICY IF EXISTS memory_insert_own ON public.sowia_memory_items;
CREATE POLICY memory_insert_own ON public.sowia_memory_items
FOR INSERT TO authenticated
WITH CHECK (user_id = (SELECT auth.uid()) AND (workspace_id = 'personal' OR public.sowia_has_professional_access()));

DROP POLICY IF EXISTS memory_update_own ON public.sowia_memory_items;
CREATE POLICY memory_update_own ON public.sowia_memory_items
FOR UPDATE TO authenticated
USING (user_id = (SELECT auth.uid()) AND (workspace_id = 'personal' OR public.sowia_has_professional_access()))
WITH CHECK (user_id = (SELECT auth.uid()) AND (workspace_id = 'personal' OR public.sowia_has_professional_access()));

DROP POLICY IF EXISTS memory_delete_own ON public.sowia_memory_items;
CREATE POLICY memory_delete_own ON public.sowia_memory_items
FOR DELETE TO authenticated
USING (user_id = (SELECT auth.uid()) AND (workspace_id = 'personal' OR public.sowia_has_professional_access()));
