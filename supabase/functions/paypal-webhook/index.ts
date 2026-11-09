// SOW IA PayPal recurring-subscription webhook.
// Deploy as a Supabase Edge Function named paypal-webhook.
// Required Edge Function secrets: PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET,
// PAYPAL_WEBHOOK_ID, PAYPAL_MODE (sandbox|live), PAYPAL_PREMIUM_PLAN_ID,
// SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Never enable checkout until this endpoint is deployed and Sandbox-tested.

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });

const env = (name: string) => Deno.env.get(name)?.trim() ?? "";

function paypalBase() {
  const mode = env("PAYPAL_MODE").toLowerCase();
  if (mode === "sandbox") return "https://api-m.sandbox.paypal.com";
  if (mode === "live") return "https://api-m.paypal.com";
  throw new Error("PAYPAL_MODE must be sandbox or live");
}

async function paypalToken(base: string) {
  const id = env("PAYPAL_CLIENT_ID");
  const secret = env("PAYPAL_CLIENT_SECRET");
  if (!id || !secret) throw new Error("PayPal credentials are not configured");
  const response = await fetch(`${base}/v1/oauth2/token`, {
    method: "POST",
    headers: {
      authorization: `Basic ${btoa(`${id}:${secret}`)}`,
      "content-type": "application/x-www-form-urlencoded",
    },
    body: "grant_type=client_credentials",
  });
  if (!response.ok) throw new Error("PayPal authentication failed");
  const data = await response.json();
  if (!data.access_token) throw new Error("PayPal access token missing");
  return data.access_token as string;
}

async function paypalGet(base: string, token: string, path: string) {
  const response = await fetch(`${base}${path}`, {
    headers: { authorization: `Bearer ${token}`, accept: "application/json" },
  });
  if (!response.ok) throw new Error("PayPal resource lookup failed");
  return await response.json();
}

async function verifyWebhook(
  base: string,
  token: string,
  headers: Headers,
  event: unknown,
) {
  const webhookId = env("PAYPAL_WEBHOOK_ID");
  const transmissionId = headers.get("paypal-transmission-id");
  const transmissionTime = headers.get("paypal-transmission-time");
  const certUrl = headers.get("paypal-cert-url");
  const authAlgo = headers.get("paypal-auth-algo");
  const transmissionSig = headers.get("paypal-transmission-sig");
  if (
    !webhookId || !transmissionId || !transmissionTime ||
    !certUrl || !authAlgo || !transmissionSig
  ) return false;

  const response = await fetch(
    `${base}/v1/notifications/verify-webhook-signature`,
    {
      method: "POST",
      headers: {
        authorization: `Bearer ${token}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        auth_algo: authAlgo,
        cert_url: certUrl,
        transmission_id: transmissionId,
        transmission_sig: transmissionSig,
        transmission_time: transmissionTime,
        webhook_id: webhookId,
        webhook_event: event,
      }),
    },
  );
  if (!response.ok) return false;
  const result = await response.json();
  return result.verification_status === "SUCCESS";
}

function supabaseHeaders(serviceKey: string, prefer = "") {
  return {
    apikey: serviceKey,
    authorization: `Bearer ${serviceKey}`,
    "content-type": "application/json",
    ...(prefer ? { prefer } : {}),
  };
}

async function dbRequest(
  url: string,
  key: string,
  path: string,
  init: RequestInit = {},
) {
  const response = await fetch(`${url}/rest/v1/${path}`, {
    ...init,
    headers: {
      ...supabaseHeaders(key),
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    const detail = await response.text();
    console.error("Supabase webhook database operation failed", response.status, detail.slice(0, 300));
    throw new Error("Subscription state could not be stored");
  }
  return response;
}

Deno.serve(async (request: Request) => {
  if (request.method !== "POST") return json({ error: "Method not allowed" }, 405);

  let claimedEventId: string | null = null;
  let databaseUrl = "";
  let databaseKey = "";

  try {
    const supabaseUrl = env("SUPABASE_URL").replace(/\/$/, "");
    const serviceKey = env("SUPABASE_SERVICE_ROLE_KEY");
    databaseUrl = supabaseUrl;
    databaseKey = serviceKey;
    const expectedPlanId = env("PAYPAL_PREMIUM_PLAN_ID");
    if (!supabaseUrl.startsWith("https://") || !serviceKey || !expectedPlanId) {
      console.error("Webhook server configuration incomplete");
      return json({ error: "Webhook is not configured" }, 503);
    }

    const event = await request.json();
    if (!event || typeof event.id !== "string" || typeof event.event_type !== "string") {
      return json({ error: "Invalid event" }, 400);
    }

    const base = paypalBase();
    const token = await paypalToken(base);
    if (!(await verifyWebhook(base, token, request.headers, event))) {
      return json({ error: "Webhook signature verification failed" }, 400);
    }

    const supported = new Set([
      "BILLING.SUBSCRIPTION.ACTIVATED",
      "BILLING.SUBSCRIPTION.UPDATED",
      "BILLING.SUBSCRIPTION.CANCELLED",
      "BILLING.SUBSCRIPTION.SUSPENDED",
      "BILLING.SUBSCRIPTION.EXPIRED",
      "PAYMENT.SALE.COMPLETED",
      "PAYMENT.SALE.REFUNDED",
      "PAYMENT.SALE.REVERSED",
    ]);
    const eventId = event.id as string;
    const eventType = event.event_type as string;
    const resource = event.resource ?? {};
    const resourceId = typeof resource.id === "string" ? resource.id : null;

    // Claim the event atomically in Postgres. Concurrent duplicate deliveries
    // cannot both proceed; failed events may be claimed again on PayPal retry.
    if (!eventId.trim() || eventId.length > 200) {
      return json({ error: "Invalid event ID" }, 400);
    }
    const claimResponse = await fetch(
      `${supabaseUrl}/rest/v1/rpc/claim_sowia_paypal_webhook_event`,
      {
        method: "POST",
        headers: supabaseHeaders(serviceKey),
        body: JSON.stringify({
          p_event_id: eventId,
          p_event_type: eventType,
          p_resource_id: resourceId,
        }),
      },
    );
    if (!claimResponse.ok) {
      console.error("Could not claim PayPal webhook event", claimResponse.status);
      throw new Error("Webhook event could not be claimed");
    }
    const claimed = await claimResponse.json();
    if (claimed !== true) {
      return json({ received: true, duplicate: true });
    }
    claimedEventId = eventId;

    if (!supported.has(eventType)) {
      await dbRequest(
        supabaseUrl,
        serviceKey,
        `sowia_paypal_webhook_events?event_id=eq.${encodeURIComponent(eventId)}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            processing_status: "ignored",
            processed_at: new Date().toISOString(),
          }),
        },
      );
      return json({ received: true, ignored: true });
    }

    let subscriptionId: string | null = null;
    if (eventType.startsWith("BILLING.SUBSCRIPTION.")) {
      subscriptionId = resourceId;
    } else if (typeof resource.billing_agreement_id === "string") {
      subscriptionId = resource.billing_agreement_id;
    }
    if (!subscriptionId || !/^[A-Z0-9-]{5,80}$/.test(subscriptionId)) {
      throw new Error("PayPal subscription identifier missing or invalid");
    }

    // Never trust the event payload for entitlement decisions: fetch the
    // subscription and its plan directly from PayPal after signature checks.
    const subscription = await paypalGet(
      base,
      token,
      `/v1/billing/subscriptions/${encodeURIComponent(subscriptionId)}`,
    );
    if (
      subscription.id !== subscriptionId ||
      subscription.plan_id !== expectedPlanId ||
      typeof subscription.custom_id !== "string" ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(subscription.custom_id)
    ) {
      throw new Error("PayPal subscription does not match the configured SOW IA plan or user");
    }

    const plan = await paypalGet(
      base,
      token,
      `/v1/billing/plans/${encodeURIComponent(expectedPlanId)}`,
    );
    const fixedPrice = plan?.billing_cycles?.find(
      (cycle: any) => cycle?.pricing_scheme?.fixed_price?.currency_code === "EUR",
    )?.pricing_scheme?.fixed_price;
    const amount = Number(fixedPrice?.value);
    if (plan.id !== expectedPlanId || !Number.isFinite(amount) || amount <= 0) {
      throw new Error("Configured PayPal plan has no valid EUR fixed price");
    }

    const userId = subscription.custom_id as string;
    const paypalStatus = String(subscription.status ?? "");
    const isActive = paypalStatus === "ACTIVE";
    const billingInfo = subscription.billing_info ?? {};
    const nextBilling = billingInfo.next_billing_time ?? null;
    const lastPaymentTime = billingInfo.last_payment?.time ?? null;

    if (isActive) {
      await dbRequest(
        supabaseUrl,
        serviceKey,
        "sowia_entitlements?on_conflict=user_id",
        {
          method: "POST",
          headers: { prefer: "resolution=merge-duplicates,return=minimal" },
          body: JSON.stringify({
            user_id: userId,
            status: "active",
            provider: "paypal",
            // Existing schema requires a non-null unique order id. A namespaced
            // subscription reference keeps this row compatible until migration
            // cleanup can safely relax that legacy constraint.
            paypal_order_id: `SUB-${subscriptionId}`,
            paypal_subscription_id: subscriptionId,
            paypal_plan_id: expectedPlanId,
            paypal_status: paypalStatus,
            amount: amount.toFixed(2),
            currency: "EUR",
            current_period_end: nextBilling,
            last_payment_at: lastPaymentTime,
            updated_at: new Date().toISOString(),
          }),
        },
      );
    } else {
      await dbRequest(
        supabaseUrl,
        serviceKey,
        `sowia_entitlements?paypal_subscription_id=eq.${encodeURIComponent(subscriptionId)}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            status: "inactive",
            paypal_status: paypalStatus,
            current_period_end: nextBilling,
            updated_at: new Date().toISOString(),
          }),
        },
      );
    }

    await dbRequest(
      supabaseUrl,
      serviceKey,
      `sowia_paypal_webhook_events?event_id=eq.${encodeURIComponent(eventId)}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          processing_status: "processed",
          processed_at: new Date().toISOString(),
        }),
      },
    );
    return json({ received: true });
  } catch (error) {
    console.error("PayPal webhook processing failed", error instanceof Error ? error.message : "unknown error");
    if (claimedEventId && databaseUrl && databaseKey) {
      try {
        await dbRequest(
          databaseUrl,
          databaseKey,
          `sowia_paypal_webhook_events?event_id=eq.${encodeURIComponent(claimedEventId)}&processing_status=eq.processing`,
          {
            method: "PATCH",
            body: JSON.stringify({ processing_status: "failed" }),
          },
        );
      } catch {
        console.error("Could not mark failed PayPal webhook event for retry");
      }
    }
    return json({ error: "Webhook processing failed; PayPal may retry delivery" }, 500);
  }
});
