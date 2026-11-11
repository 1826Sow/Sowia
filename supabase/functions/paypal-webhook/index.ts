// SOW IA PayPal subscription webhook.
// Deploy only after applying the matching SQL migration and setting Edge Function secrets.
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, paypal-transmission-id, paypal-transmission-time, paypal-cert-url, paypal-auth-algo, paypal-transmission-sig",
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

async function paypalAccessToken(baseUrl: string, clientId: string, secret: string) {
  const basic = btoa(clientId + ":" + secret);
  const response = await fetch(baseUrl + "/v1/oauth2/token", {
    method: "POST",
    headers: {
      Authorization: "Basic " + basic,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: "grant_type=client_credentials",
  });
  if (!response.ok) throw new Error("PayPal OAuth request failed");
  const body = await response.json();
  if (!body.access_token) throw new Error("PayPal OAuth token missing");
  return String(body.access_token);
}

async function verifyWebhook(
  baseUrl: string,
  token: string,
  webhookId: string,
  event: Record<string, unknown>,
  request: Request,
) {
  const names = [
    "paypal-transmission-id",
    "paypal-transmission-time",
    "paypal-cert-url",
    "paypal-auth-algo",
    "paypal-transmission-sig",
  ];
  const values = names.map((name) => request.headers.get(name));
  if (values.some((value) => !value)) return false;

  const [transmissionId, transmissionTime, certUrl, authAlgo, transmissionSig] = values;
  const response = await fetch(baseUrl + "/v1/notifications/verify-webhook-signature", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      transmission_id: transmissionId,
      transmission_time: transmissionTime,
      cert_url: certUrl,
      auth_algo: authAlgo,
      transmission_sig: transmissionSig,
      webhook_id: webhookId,
      webhook_event: event,
    }),
  });
  if (!response.ok) throw new Error("PayPal webhook verification request failed");
  const result = await response.json();
  return result.verification_status === "SUCCESS";
}

Deno.serve(async (request: Request) => {
  if (request.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (request.method !== "POST") return json({ error: "Method not allowed" }, 405);

  try {
    const supabaseUrl = requiredEnv("SUPABASE_URL").replace(/\/$/, "");
    const serviceRoleKey = requiredEnv("SUPABASE_SERVICE_ROLE_KEY");
    const clientId = requiredEnv("PAYPAL_CLIENT_ID");
    const clientSecret = requiredEnv("PAYPAL_CLIENT_SECRET");
    const webhookId = requiredEnv("PAYPAL_SUBSCRIPTION_WEBHOOK_ID");
    const mode = (Deno.env.get("PAYPAL_MODE") || "sandbox").trim()
      .toLowerCase();
    if (mode !== "sandbox" && mode !== "live") {
      return json({ error: "Invalid PayPal mode" }, 500);
    }
    const baseUrl = mode === "live"
      ? "https://api-m.paypal.com"
      : "https://api-m.sandbox.paypal.com";

    const catalogResponse = await fetch(
      supabaseUrl +
        "/rest/v1/sowia_paypal_catalog?mode=eq." + mode +
        "&select=paypal_plan_id&limit=1",
      {
        headers: {
          apikey: serviceRoleKey,
          Authorization: "Bearer " + serviceRoleKey,
          Accept: "application/json",
        },
      },
    );
    if (!catalogResponse.ok) {
      throw new Error("Unable to read the configured PayPal plan");
    }
    const catalogRows = await catalogResponse.json();
    const planId = Array.isArray(catalogRows) && catalogRows.length
      ? String(catalogRows[0].paypal_plan_id || "")
      : "";
    if (!/^P-[A-Z0-9]+$/.test(planId)) {
      return json({ error: "PayPal plan is not provisioned for this mode" }, 503);
    }

    const event = await request.json();
    if (!event || typeof event !== "object" || Array.isArray(event)) {
      return json({ error: "Invalid event body" }, 400);
    }

    const token = await paypalAccessToken(baseUrl, clientId, clientSecret);
    const verified = await verifyWebhook(
      baseUrl,
      token,
      webhookId,
      event,
      request,
    );
    if (!verified) return json({ error: "Webhook signature verification failed" }, 401);

    const eventType = String(event.event_type || "");
    const supportedEvents = new Set([
      "BILLING.SUBSCRIPTION.ACTIVATED",
      "BILLING.SUBSCRIPTION.UPDATED",
      "BILLING.SUBSCRIPTION.CANCELLED",
      "BILLING.SUBSCRIPTION.SUSPENDED",
      "BILLING.SUBSCRIPTION.EXPIRED",
      "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
      "PAYMENT.SALE.COMPLETED",
      "PAYMENT.SALE.REFUNDED",
      "PAYMENT.SALE.REVERSED",
    ]);
    if (!supportedEvents.has(eventType)) {
      return json({ received: true, ignored: true });
    }

    const resource = (event.resource && typeof event.resource === "object")
      ? event.resource as Record<string, unknown>
      : {};
    const related = (resource.supplementary_data &&
        typeof resource.supplementary_data === "object")
      ? resource.supplementary_data as Record<string, unknown>
      : {};
    const relatedIds =
      (related.related_ids && typeof related.related_ids === "object")
        ? related.related_ids as Record<string, unknown>
        : {};
    // Sale events carry their subscription ID in billing_agreement_id;
    // resource.id is the sale/transaction ID and must never be mistaken for it.
    const subscriptionId = String(
      resource.billing_agreement_id ||
        relatedIds.billing_agreement_id ||
        relatedIds.subscription_id ||
        (eventType.startsWith("BILLING.SUBSCRIPTION.") ? resource.id : "") ||
        "",
    ).trim();
    if (!/^I-[A-Z0-9-]{5,64}$/.test(subscriptionId)) {
      return json({
        received: true,
        ignored: true,
        reason: "No subscription identifier",
      });
    }

    // Reconcile against PayPal's current server-side record; never trust event status alone.
    const subscriptionResponse = await fetch(
      baseUrl + "/v1/billing/subscriptions/" +
        encodeURIComponent(subscriptionId),
      {
        headers: {
          Authorization: "Bearer " + token,
          Accept: "application/json",
        },
      },
    );
    if (!subscriptionResponse.ok) {
      throw new Error("Unable to reconcile subscription with PayPal");
    }
    const subscription = await subscriptionResponse.json();
    const userId = String(subscription.custom_id || "");
    const uuidPattern =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    if (
      subscription.id !== subscriptionId ||
      subscription.plan_id !== planId ||
      !uuidPattern.test(userId)
    ) {
      return json(
        { error: "Subscription ownership or plan validation failed" },
        403,
      );
    }

    // Confirm the plan's server-side recurring price; never trust the plan ID alone.
    const planResponse = await fetch(
      baseUrl + "/v1/billing/plans/" + encodeURIComponent(planId),
      {
        headers: {
          Authorization: "Bearer " + token,
          Accept: "application/json",
        },
      },
    );
    if (!planResponse.ok) {
      throw new Error("Unable to verify PayPal plan pricing");
    }
    const plan = await planResponse.json();
    const regularCycles = Array.isArray(plan.billing_cycles)
      ? plan.billing_cycles.filter((cycle: Record<string, unknown>) =>
          String(cycle.tenure_type || "").toUpperCase() === "REGULAR")
      : [];
    const validPrice = plan.id === planId &&
      String(plan.status || "").toUpperCase() === "ACTIVE" &&
      regularCycles.length > 0 &&
      regularCycles.every((cycle: Record<string, unknown>) => {
        const frequency = (cycle.frequency || {}) as Record<string, unknown>;
        const scheme = (cycle.pricing_scheme || {}) as Record<string, unknown>;
        const fixedPrice = (scheme.fixed_price || {}) as Record<string, unknown>;
        return String(frequency.interval_unit || "").toUpperCase() === "MONTH" &&
          Number(frequency.interval_count) === 1 &&
          Number(fixedPrice.value) === 9.90 &&
          String(fixedPrice.currency_code || "").toUpperCase() === "EUR";
      });
    if (!validPrice) {
      return json({ error: "PayPal Premium plan price validation failed" }, 403);
    }

    const billing = subscription.billing_info || {};
    const lastPayment = billing.last_payment || {};
    const paymentAmount = lastPayment.amount || {};
    if (paymentAmount.value !== undefined &&
        (Number(paymentAmount.value) !== 9.90 ||
         String(paymentAmount.currency_code || "").toUpperCase() !== "EUR")) {
      return json({ error: "PayPal last payment amount mismatch" }, 403);
    }
    const payload = {
      user_id: userId,
      provider: "paypal",
      paypal_subscription_id: subscriptionId,
      paypal_plan_id: planId,
      status: String(subscription.status || "UNKNOWN").toLowerCase(),
      currency: paymentAmount.currency_code || null,
      amount: paymentAmount.value || null,
      next_billing_time: billing.next_billing_time || null,
      last_payment_at: lastPayment.time || null,
      updated_at: new Date().toISOString(),
    };

    const writeResponse = await fetch(
      supabaseUrl +
        "/rest/v1/sowia_subscriptions?on_conflict=paypal_subscription_id",
      {
        method: "POST",
        headers: {
          apikey: serviceRoleKey,
          Authorization: "Bearer " + serviceRoleKey,
          "Content-Type": "application/json",
          Prefer: "resolution=merge-duplicates,return=minimal",
        },
        body: JSON.stringify(payload),
      },
    );
    if (!writeResponse.ok) {
      console.error(
        "Supabase subscription upsert failed",
        await writeResponse.text(),
      );
      throw new Error("Unable to persist subscription state");
    }

    return json({ received: true, reconciled: true });
  } catch (error) {
    console.error("PayPal webhook handler error", error);
    return json({ error: "Webhook processing failed" }, 500);
  }
});
