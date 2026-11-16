// SOW IA Stripe webhook: verify signature, reconcile with Stripe, then update entitlements.
// Deploy after applying 20261116000300_sowia_stripe_webhook_events.sql and setting secrets.
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, stripe-signature",
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function requiredEnv(name: string): string {
  const value = Deno.env.get(name)?.trim();
  if (!value) throw new Error("Missing Edge Function secret: " + name);
  return value;
}

function constantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return result === 0;
}

function hex(bytes: Uint8Array): string {
  return Array.from(bytes).map((value) => value.toString(16).padStart(2, "0")).join("");
}

async function verifyStripeSignature(rawBody: string, header: string, secret: string): Promise<boolean> {
  const parts = header.split(",").map((part) => part.trim());
  const timestamp = parts.find((part) => part.startsWith("t="))?.slice(2) || "";
  const signatures = parts.filter((part) => part.startsWith("v1=")).map((part) => part.slice(3));
  if (!/^\d+$/.test(timestamp) || signatures.length === 0) return false;
  const seconds = Number(timestamp);
  if (!Number.isSafeInteger(seconds) || Math.abs(Date.now() / 1000 - seconds) > 300) return false;
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const digest = new Uint8Array(await crypto.subtle.sign(
    "HMAC", key, new TextEncoder().encode(timestamp + "." + rawBody),
  ));
  const expected = hex(digest);
  return signatures.some((signature) => constantTimeEqual(signature, expected));
}

async function stripeGet(path: string, secret: string): Promise<Record<string, unknown>> {
  const response = await fetch("https://api.stripe.com/v1/" + path, {
    headers: { Authorization: "Bearer " + secret },
  });
  if (!response.ok) throw new Error("Stripe API reconciliation failed: " + response.status);
  return await response.json();
}

async function supabaseRequest(url: string, key: string, path: string, init: RequestInit = {}) {
  return await fetch(url + "/rest/v1/" + path, {
    ...init,
    headers: {
      apikey: key,
      Authorization: "Bearer " + key,
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });
}

Deno.serve(async (request: Request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (request.method !== "POST") return json({ error: "Method not allowed" }, 405);

  let supabaseUrl = "";
  let serviceKey = "";
  let eventId = "";
  try {
    supabaseUrl = requiredEnv("SUPABASE_URL").replace(/\/$/, "");
    serviceKey = requiredEnv("SUPABASE_SERVICE_ROLE_KEY");
    const stripeSecret = requiredEnv("STRIPE_SECRET_KEY");
    const webhookSecret = requiredEnv("STRIPE_WEBHOOK_SECRET");
    const priceId = requiredEnv("STRIPE_PREMIUM_PRICE_ID");
    const amountSetting = Number(Deno.env.get("STRIPE_PREMIUM_PRICE_EUR") || "9.90");
    const expectedAmount = Math.round(amountSetting * 100);
    if (!Number.isFinite(amountSetting) || !Number.isSafeInteger(expectedAmount) || expectedAmount <= 0) {
      return json({ error: "Invalid configured Premium amount" }, 500);
    }

    const rawBody = await request.text();
    const signature = request.headers.get("stripe-signature") || "";
    if (!await verifyStripeSignature(rawBody, signature, webhookSecret)) {
      return json({ error: "Invalid Stripe signature" }, 401);
    }
    const event = JSON.parse(rawBody);
    eventId = String(event.id || "");
    const eventType = String(event.type || "");
    if (!/^evt_[A-Za-z0-9]+$/.test(eventId) || eventId.length > 255) {
      return json({ error: "Invalid Stripe event ID" }, 400);
    }

    const insert = await supabaseRequest(
      supabaseUrl, serviceKey, "sowia_stripe_webhook_events?on_conflict=event_id",
      {
        method: "POST",
        headers: { Prefer: "resolution=ignore-duplicates,return=representation" },
        body: JSON.stringify({
          event_id: eventId, event_type: eventType, processing_status: "received",
          received_at: new Date().toISOString(),
        }),
      },
    );
    if (!insert.ok) throw new Error("Unable to register Stripe webhook event");
    const inserted = await insert.json();
    if (!Array.isArray(inserted) || inserted.length === 0) {
      const prior = await supabaseRequest(
        supabaseUrl, serviceKey,
        "sowia_stripe_webhook_events?event_id=eq." + encodeURIComponent(eventId) + "&select=processing_status&limit=1",
      );
      if (!prior.ok) throw new Error("Unable to inspect duplicate Stripe event");
      const rows = await prior.json();
      if (rows[0]?.processing_status === "processed") {
        return json({ received: true, duplicate: true, processed: true }, 200);
      }
    }

    const stale = new Date(Date.now() - 10 * 60 * 1000).toISOString();
    const claim = await supabaseRequest(
      supabaseUrl, serviceKey,
      "sowia_stripe_webhook_events?event_id=eq." + encodeURIComponent(eventId) +
        "&or=" + encodeURIComponent("(processing_status.eq.received,processing_status.eq.failed,and(processing_status.eq.processing,processing_started_at.lt." + stale + "))"),
      {
        method: "PATCH",
        headers: { Prefer: "return=representation" },
        body: JSON.stringify({ processing_status: "processing", processing_started_at: new Date().toISOString(), last_error: null }),
      },
    );
    if (!claim.ok) throw new Error("Unable to claim Stripe webhook event");
    const claimed = await claim.json();
    if (!Array.isArray(claimed) || claimed.length === 0) {
      return json({ received: true, duplicate: true, processing: true }, 202);
    }

    const data = event.data?.object || {};
    if (eventType === "checkout.session.completed" || eventType === "checkout.session.async_payment_succeeded") {
      const sessionId = String(data.id || "");
      if (!sessionId.startsWith("cs_")) throw new Error("Invalid Checkout Session ID");
      const session = await stripeGet(
        "checkout/sessions/" + encodeURIComponent(sessionId) + "?expand[]=line_items",
        stripeSecret,
      );
      const userId = String(session.client_reference_id || "");
      const metadata = session.metadata && typeof session.metadata === "object" ? session.metadata as Record<string, unknown> : {};
      const lineItems = session.line_items && typeof session.line_items === "object" ? session.line_items as Record<string, unknown> : {};
      const items = Array.isArray(lineItems.data) ? lineItems.data as Record<string, unknown>[] : [];
      const price = items[0]?.price && typeof items[0].price === "object" ? items[0].price as Record<string, unknown> : {};
      const paymentIntent = typeof session.payment_intent === "string"
        ? session.payment_intent
        : String((session.payment_intent as Record<string, unknown> | null)?.id || "");
      if (
        session.id !== sessionId || session.mode !== "payment" || session.payment_status !== "paid" ||
        !userId || metadata.sowia_user_id !== userId || metadata.sowia_product !== "premium" ||
        String(session.currency || "").toLowerCase() !== "eur" || Number(session.amount_total) !== expectedAmount ||
        price.id !== priceId || Number(items[0]?.quantity || 0) !== 1 || !/^pi_[A-Za-z0-9]+$/.test(paymentIntent)
      ) throw new Error("Checkout Session does not match the configured SOW IA Premium purchase");

      const intent = await stripeGet(
        "payment_intents/" + encodeURIComponent(paymentIntent) + "?expand[]=latest_charge",
        stripeSecret,
      );
      const latestCharge = intent.latest_charge && typeof intent.latest_charge === "object"
        ? intent.latest_charge as Record<string, unknown>
        : {};
      if (
        intent.status !== "succeeded" ||
        Number(intent.amount_received || 0) !== expectedAmount ||
        String(intent.currency || "").toLowerCase() !== "eur" ||
        !String(latestCharge.id || "").startsWith("ch_") ||
        Number(latestCharge.amount_captured || 0) !== expectedAmount ||
        Number(latestCharge.amount_refunded || 0) > 0 ||
        Boolean(latestCharge.disputed)
      ) throw new Error("PaymentIntent is not in a clean paid state");

      const entitlement = await supabaseRequest(
        supabaseUrl, serviceKey, "sowia_entitlements?on_conflict=user_id",
        {
          method: "POST",
          headers: { Prefer: "resolution=merge-duplicates,return=minimal" },
          body: JSON.stringify({
            user_id: userId, status: "active", provider: "stripe",
            stripe_checkout_session_id: sessionId, stripe_payment_intent_id: paymentIntent,
            amount: (expectedAmount / 100).toFixed(2), currency: "EUR", updated_at: new Date().toISOString(),
          }),
        },
      );
      if (!entitlement.ok) throw new Error("Unable to grant verified Stripe Premium entitlement");

      // Keep the SOW IA financial ledger in sync with the verified provider payment.
      // The PaymentIntent is the stable idempotency key; raw card data never enters SOW IA.
      const paymentLedger = await supabaseRequest(
        supabaseUrl, serviceKey,
        "sowia_financial_transactions?on_conflict=provider,provider_payment_id,transaction_type",
        {
          method: "POST",
          headers: { Prefer: "resolution=ignore-duplicates,return=minimal" },
          body: JSON.stringify({
            user_id: userId, provider: "stripe", provider_payment_id: paymentIntent,
            transaction_type: "payment", status: "confirmed",
            gross_amount: (expectedAmount / 100).toFixed(2), gross_currency: "EUR",
            reference_amount_eur: (expectedAmount / 100).toFixed(2),
            occurred_at: new Date(Number(session.created || event.created) * 1000).toISOString(),
          }),
        },
      );
      if (!paymentLedger.ok) throw new Error("Unable to record verified Stripe payment in financial ledger");
    } else if (
      eventType === "charge.refunded" || eventType === "charge.dispute.created" ||
      eventType === "charge.dispute.closed"
    ) {
      const chargeId = String(eventType === "charge.refunded" ? data.id : data.charge || "");
      if (!chargeId.startsWith("ch_")) throw new Error("Invalid Stripe charge reference");
      const charge = await stripeGet(
        "charges/" + encodeURIComponent(chargeId) + "?expand[]=refunds",
        stripeSecret,
      );
      const paymentIntent = typeof charge.payment_intent === "string"
        ? charge.payment_intent
        : String((charge.payment_intent as Record<string, unknown> | null)?.id || "");
      if (!/^pi_[A-Za-z0-9]+$/.test(paymentIntent)) throw new Error("Charge has no valid PaymentIntent");
      const entitlementLookup = await supabaseRequest(
        supabaseUrl, serviceKey,
        "sowia_entitlements?provider=eq.stripe&stripe_payment_intent_id=eq." +
          encodeURIComponent(paymentIntent) + "&select=user_id&limit=1",
      );
      if (!entitlementLookup.ok) throw new Error("Unable to find Stripe entitlement owner");
      const entitlementRows = await entitlementLookup.json();
      const ownerId = String(entitlementRows[0]?.user_id || "");
      if (!ownerId) throw new Error("No SOW IA account is linked to this Stripe payment");

      if (eventType === "charge.refunded") {
        const refunds = charge.refunds && typeof charge.refunds === "object"
          ? charge.refunds as Record<string, unknown>
          : {};
        const refundRows = Array.isArray(refunds.data)
          ? refunds.data as Record<string, unknown>[]
          : [];
        for (const refund of refundRows) {
          if (String(refund.status || "").toLowerCase() !== "succeeded") continue;
          if (String(refund.currency || "").toLowerCase() !== "eur") {
            throw new Error("Stripe refund currency does not match the EUR Premium ledger");
          }
          const refundId = String(refund.id || "");
          const refundCents = Number(refund.amount || 0);
          if (!/^re_[A-Za-z0-9]+$/.test(refundId) ||
              !Number.isSafeInteger(refundCents) || refundCents <= 0) {
            throw new Error("Invalid succeeded Stripe refund record");
          }
          const refundLedger = await supabaseRequest(
            supabaseUrl, serviceKey,
            "sowia_financial_transactions?on_conflict=provider,provider_payment_id,transaction_type",
            {
              method: "POST",
              headers: { Prefer: "resolution=ignore-duplicates,return=minimal" },
              body: JSON.stringify({
                user_id: ownerId, provider: "stripe", provider_payment_id: refundId,
                parent_capture_id: chargeId, transaction_type: "refund", status: "refunded",
                gross_amount: (refundCents / 100).toFixed(2), gross_currency: "EUR",
                reference_amount_eur: (refundCents / 100).toFixed(2),
                occurred_at: new Date(Number(refund.created || event.created) * 1000).toISOString(),
              }),
            },
          );
          if (!refundLedger.ok) throw new Error("Unable to record Stripe refund in financial ledger");
        }
      }

      let revoke = eventType !== "charge.dispute.closed";
      if (eventType === "charge.refunded") revoke = Number(charge.amount_refunded || 0) > 0;
      if (eventType === "charge.dispute.closed") {
        revoke = String(data.status || "").toLowerCase() !== "won" ||
          Boolean(charge.refunded) || Number(charge.amount_refunded || 0) > 0;
      }
      const update = await supabaseRequest(
        supabaseUrl, serviceKey,
        "sowia_entitlements?provider=eq.stripe&stripe_payment_intent_id=eq." + encodeURIComponent(paymentIntent),
        {
          method: "PATCH",
          headers: { Prefer: "return=minimal" },
          body: JSON.stringify({
            status: revoke ? "inactive" : "active",
            updated_at: new Date().toISOString(),
          }),
        },
      );
      if (!update.ok) throw new Error("Unable to reconcile Stripe refund or dispute entitlement");

      if (eventType === "charge.dispute.created" || eventType === "charge.dispute.closed") {
        const ledgerStatus = revoke ? "reversed" : "confirmed";
        const ledgerUpdate = await supabaseRequest(
          supabaseUrl, serviceKey,
          "sowia_financial_transactions?provider=eq.stripe&provider_payment_id=eq." +
            encodeURIComponent(paymentIntent) + "&transaction_type=eq.payment&user_id=eq." +
            encodeURIComponent(ownerId),
          {
            method: "PATCH",
            headers: { Prefer: "return=minimal" },
            body: JSON.stringify({ status: ledgerStatus }),
          },
        );
        if (!ledgerUpdate.ok) throw new Error("Unable to reconcile Stripe dispute in financial ledger");
      }
    }

    const done = await supabaseRequest(
      supabaseUrl, serviceKey,
      "sowia_stripe_webhook_events?event_id=eq." + encodeURIComponent(eventId),
      {
        method: "PATCH",
        headers: { Prefer: "return=minimal" },
        body: JSON.stringify({ processing_status: "processed", processed_at: new Date().toISOString(), last_error: null }),
      },
    );
    if (!done.ok) throw new Error("Unable to finalize Stripe webhook event");
    return json({ received: true, processed: true });
  } catch (error) {
    if (supabaseUrl && serviceKey && eventId) {
      await supabaseRequest(
        supabaseUrl, serviceKey,
        "sowia_stripe_webhook_events?event_id=eq." + encodeURIComponent(eventId),
        {
          method: "PATCH",
          headers: { Prefer: "return=minimal" },
          body: JSON.stringify({
            processing_status: "failed",
            last_error: String(error).slice(0, 500),
          }),
        },
      ).catch(() => undefined);
    }
    return json({ error: "Stripe webhook processing failed" }, 500);
  }
});
