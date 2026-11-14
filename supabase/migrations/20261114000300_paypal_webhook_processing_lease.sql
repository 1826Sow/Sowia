-- Recover PayPal webhook events left in processing after a hard function crash.
ALTER TABLE public.sowia_paypal_webhook_events
  ADD COLUMN IF NOT EXISTS processing_started_at timestamptz;

-- Give already-running legacy events a grace period before they can be reclaimed.
UPDATE public.sowia_paypal_webhook_events
SET processing_started_at = now()
WHERE processing_status = 'processing'
  AND processing_started_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_sowia_paypal_webhook_processing_lease
  ON public.sowia_paypal_webhook_events (processing_started_at)
  WHERE processing_status = 'processing';
