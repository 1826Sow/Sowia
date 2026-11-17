-- Defense-in-depth owner boundary for user-scoped conversation data.
-- Existing permissive policies control workspace entitlement; these restrictive
-- policies ensure every authenticated operation remains scoped to auth.uid().
CREATE POLICY "Restrict SOW IA messages to owner"
ON public.sowia_messages
AS RESTRICTIVE
FOR ALL
TO authenticated
USING (user_id = (SELECT auth.uid()))
WITH CHECK (user_id = (SELECT auth.uid()));

CREATE POLICY "Restrict SOW IA memories to owner"
ON public.sowia_memory_items
AS RESTRICTIVE
FOR ALL
TO authenticated
USING (user_id = (SELECT auth.uid()))
WITH CHECK (user_id = (SELECT auth.uid()));
