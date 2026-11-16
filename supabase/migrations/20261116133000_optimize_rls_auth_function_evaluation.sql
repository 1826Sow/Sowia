-- Optimize RLS policy evaluation by wrapping auth.uid()/auth.jwt()
-- in scalar subqueries. This preserves each policy's roles, command,
-- permissive/restrictive mode, and access predicates.
do $$
declare
  p record;
  v_sql text;
begin
  for p in
    select schemaname, tablename, policyname, qual, with_check
    from pg_policies
    where schemaname = 'public'
      and (
        (position('auth.uid()' in coalesce(qual, '')) > 0
          and position('select auth.uid()' in lower(coalesce(qual, ''))) = 0)
        or
        (position('auth.uid()' in coalesce(with_check, '')) > 0
          and position('select auth.uid()' in lower(coalesce(with_check, ''))) = 0)
        or
        (position('auth.jwt()' in coalesce(qual, '')) > 0
          and position('select auth.jwt()' in lower(coalesce(qual, ''))) = 0)
        or
        (position('auth.jwt()' in coalesce(with_check, '')) > 0
          and position('select auth.jwt()' in lower(coalesce(with_check, ''))) = 0)
      )
  loop
    v_sql := format('ALTER POLICY %I ON %I.%I',
      p.policyname, p.schemaname, p.tablename);

    if p.qual is not null then
      v_sql := v_sql || format(' USING (%s)',
        replace(replace(p.qual, 'auth.uid()', '(select auth.uid())'),
                         'auth.jwt()', '(select auth.jwt())'));
    end if;

    if p.with_check is not null then
      v_sql := v_sql || format(' WITH CHECK (%s)',
        replace(replace(p.with_check, 'auth.uid()', '(select auth.uid())'),
                         'auth.jwt()', '(select auth.jwt())'));
    end if;

    execute v_sql;
  end loop;
end
$$;
