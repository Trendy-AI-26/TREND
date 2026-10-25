-- Run against the remote database after the security migration.
-- Checks metadata and zero-row queries only; no customer records are read.
BEGIN;

DO $$
DECLARE
  client_role text;
  operation text;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_class
    WHERE oid = 'public.product_assets'::regclass
      AND relrowsecurity AND relforcerowsecurity
  ) THEN
    RAISE EXCEPTION 'Product assets must enable and force RLS';
  END IF;

  FOREACH client_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    FOREACH operation IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'] LOOP
      IF has_table_privilege(client_role, 'public.product_assets', operation) THEN
        RAISE EXCEPTION 'Unexpected % privilege for %', operation, client_role;
      END IF;
    END LOOP;
    EXECUTE format('SET LOCAL ROLE %I', client_role);
    BEGIN
      PERFORM 1 FROM public.product_assets LIMIT 0;
      RAISE EXCEPTION 'Direct client reads must be denied';
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;
    END;
    RESET ROLE;
  END LOOP;

  FOREACH operation IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE'] LOOP
    IF NOT has_table_privilege('service_role', 'public.product_assets', operation) THEN
      RAISE EXCEPTION 'Service role missing % privilege', operation;
    END IF;
  END LOOP;
END
$$;

ROLLBACK;
SELECT 'product-assets service-only access verified' AS result;
