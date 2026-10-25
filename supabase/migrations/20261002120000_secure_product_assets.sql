-- Product asset operations use FastAPI ownership checks and the service client.
-- Direct browser/Data API access to asset records is intentionally unsupported.
BEGIN;

ALTER TABLE public.product_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_assets FORCE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.product_assets FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.product_assets TO service_role;

COMMIT;
