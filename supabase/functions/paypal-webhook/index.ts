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
      "BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED",
      "PAYMENT.SALE.COMPLETED",
      "PAYMENT.SALE.REFUNDED",
      "PAYMENT.SALE.REVERSED",
      "PAYMENT.CAPTURE.REFUNDED",
      "PAYMENT.CAPTURE.REVERSED",
    ]);
    if (!supportedEvents.has(eventType)) {
      return json({ received: true, ignored: true });
    }

    const resource = (event.resource && typeof event.resource === "object")
      ? event.resource as Record<string, unknown>
      : {};

    // PAYMENT.CAPTURE.REVERSED is distinct from a merchant-initiated refund.
    // PayPal maps this event to the Refund Captured Payment resource: resolve
    // and verify that refund first, then follow its parent capture link.
    if (eventType === "PAYMENT.CAPTURE.REVERSED") {
      // PayPal models a capture reversal webhook as a refund resource. Its ID
      // is the refund ID; the parent capture must be resolved from the verified
      // refund's HATEOAS "up" link, never by treating resource.id as a capture.
      const refundId = String(resource.id || "").trim();
      const eventId = String(event.id || "").trim();
      const reversalEventTime = String(event.create_time || "").trim();
      if (!/^[A-Z0-9]{8,64}$/i.test(refundId) ||
          !eventId || eventId.length > 128 ||
          !reversalEventTime || !Number.isFinite(Date.parse(reversalEventTime))) {
        return json({ error: "Invalid PayPal capture reversal identifiers" }, 422);
      }
      const refundResponse = await fetch(
        baseUrl + "/v2/payments/refunds/" + encodeURIComponent(refundId),
        { headers: { Authorization: "Bearer " + token, Accept: "application/json" } },
      );
      if (!refundResponse.ok) {
        throw new Error("Unable to verify reversed PayPal refund");
      }
      const refund = await refundResponse.json();
      const refundAmount = refund.amount || {};
      if (refund.id !== refundId ||
          String(refund.status || "").toUpperCase() !== "COMPLETED" ||
          String(refundAmount.currency_code || "").toUpperCase() !== "EUR" ||
          !Number.isFinite(Number(refundAmount.value)) ||
          Number(refundAmount.value) <= 0) {
        return json({ error: "PayPal capture reversal refund validation failed" }, 403);
      }
      const refundLinks = Array.isArray(refund.links) ? refund.links : [];
      const parentLink = refundLinks.find((link: Record<string, unknown>) =>
        String(link.rel || "").toLowerCase() === "up"
      );
      let captureId = "";
      try {
        const parentUrl = new URL(String(parentLink?.href || ""));
        const captureMatch = parentUrl.pathname.match(/^\/v2\/payments\/captures\/([A-Z0-9]{8,64})$/i);
        if (parentUrl.origin === new URL(baseUrl).origin && captureMatch) {
          captureId = captureMatch[1];
        }
      } catch (_error) {
        captureId = "";
      }
      if (!captureId) {
        return json({ error: "PayPal reversal parent capture is invalid" }, 422);
      }
      const captureResponse = await fetch(
        baseUrl + "/v2/payments/captures/" + encodeURIComponent(captureId),
        { headers: { Authorization: "Bearer " + token, Accept: "application/json" } },
      );
      if (!captureResponse.ok) {
        throw new Error("Unable to verify reversed PayPal parent capture");
      }
      const capture = await captureResponse.json();
      const captureAmount = capture.amount || {};
      const captureStatus = String(capture.status || "").toUpperCase();
      if (capture.id !== captureId ||
          !new Set(["COMPLETED", "PARTIALLY_REFUNDED", "REFUNDED"]).has(captureStatus) ||
          String(captureAmount.currency_code || "").toUpperCase() !== "EUR" ||
          !Number.isFinite(Number(captureAmount.value)) ||
          Number(captureAmount.value) <= 0 ||
          Number(refundAmount.value) > Number(captureAmount.value)) {
        return json({ error: "PayPal reversed capture validation failed" }, 403);
      }
      const orderId = String(capture.supplementary_data?.related_ids?.order_id || "").trim();
      if (!orderId) {
        return json({ error: "Reversed PayPal capture has no verified order" }, 422);
      }
      const ledgerHeaders = {
        apikey: serviceRoleKey,
        Authorization: "Bearer " + serviceRoleKey,
        Accept: "application/json",
      };
      const captureLedgerResponse = await fetch(
        supabaseUrl + "/rest/v1/sowia_financial_transactions" +
          "?provider=eq.paypal&transaction_type=eq.payment&provider_payment_id=eq." +
          encodeURIComponent(captureId) +
          "&select=user_id,paypal_order_id,gross_amount,gross_currency&limit=1",
        { headers: ledgerHeaders },
      );
      if (!captureLedgerResponse.ok) {
        throw new Error("Unable to locate reversed PayPal capture ownership");
      }
      const captureLedgerRows = await captureLedgerResponse.json();
      const captureLedger = Array.isArray(captureLedgerRows) && captureLedgerRows.length === 1
        ? captureLedgerRows[0]
        : null;
      const uuidPattern =
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
      if (!captureLedger || !uuidPattern.test(String(captureLedger.user_id || "")) ||
          captureLedger.paypal_order_id !== orderId ||
          Number(captureLedger.gross_amount) !== Number(captureAmount.value) ||
          String(captureLedger.gross_currency || "").toUpperCase() !== "EUR") {
        return json({ error: "Reversed capture ownership or order validation failed" }, 403);
      }

      // Use this verified refund's amount, not the capture's full amount or a
      // locally estimated remainder. The ledger trigger serializes cumulative
      // refunds and rejects any total above the original capture.
      const reversalLedgerUrl = supabaseUrl +
        "/rest/v1/sowia_financial_transactions?provider=eq.paypal" +
        "&transaction_type=eq.refund&provider_payment_id=eq." +
        encodeURIComponent(refundId) +
        "&select=user_id,parent_capture_id,gross_amount,gross_currency,status&limit=1";
      const reversalLedgerMatches = (row: Record<string, unknown>) =>
        String(row.user_id || "") === String(captureLedger.user_id) &&
        String(row.parent_capture_id || "") === captureId &&
        Number(row.gross_amount) === Number(refundAmount.value) &&
        String(row.gross_currency || "").toUpperCase() === "EUR" &&
        String(row.status || "") === "manual_review";
      const existingReversalResponse = await fetch(reversalLedgerUrl, { headers: ledgerHeaders });
      if (!existingReversalResponse.ok) {
        throw new Error("Unable to check PayPal reversal ledger idempotency");
      }
      const existingReversalRows = await existingReversalResponse.json();
      const existingReversal = Array.isArray(existingReversalRows) && existingReversalRows.length === 1
        ? existingReversalRows[0]
        : null;
      if (existingReversal && !reversalLedgerMatches(existingReversal)) {
        return json({ error: "Existing PayPal reversal ledger entry conflicts" }, 409);
      }
      if (!existingReversal) {
        const insertReversalResponse = await fetch(
          supabaseUrl + "/rest/v1/sowia_financial_transactions" +
            "?on_conflict=provider,provider_payment_id,transaction_type",
          {
            method: "POST",
            headers: {
              ...ledgerHeaders,
              "Content-Type": "application/json",
              Prefer: "resolution=ignore-duplicates,return=minimal",
            },
            body: JSON.stringify({
              user_id: String(captureLedger.user_id),
              provider: "paypal",
              provider_payment_id: refundId,
              parent_capture_id: captureId,
              transaction_type: "refund",
              status: "manual_review",
              gross_amount: Number(refundAmount.value),
              gross_currency: "EUR",
              occurred_at: reversalEventTime,
            }),
          },
        );
        if (!insertReversalResponse.ok) {
          throw new Error("Unable to persist verified PayPal capture reversal");
        }
        const confirmReversalResponse = await fetch(reversalLedgerUrl, { headers: ledgerHeaders });
        if (!confirmReversalResponse.ok) {
          throw new Error("Unable to confirm PayPal capture reversal ledger entry");
        }
        const confirmedReversalRows = await confirmReversalResponse.json();
        const confirmedReversal = Array.isArray(confirmedReversalRows) && confirmedReversalRows.length === 1
          ? confirmedReversalRows[0]
          : null;
        if (!confirmedReversal || !reversalLedgerMatches(confirmedReversal)) {
          return json({ error: "PayPal capture reversal ledger confirmation failed" }, 409);
        }
      }

      const revokeResponse = await fetch(
        supabaseUrl + "/rest/v1/sowia_entitlements?user_id=eq." +
          encodeURIComponent(String(captureLedger.user_id)) + "&paypal_order_id=eq." +
          encodeURIComponent(orderId) + "&status=eq.active",
        {
          method: "PATCH",
          headers: {
            apikey: serviceRoleKey,
            Authorization: "Bearer " + serviceRoleKey,
            "Content-Type": "application/json",
            Prefer: "return=representation",
          },
          body: JSON.stringify({ status: "inactive" }),
        },
      );
      if (!revokeResponse.ok) {
        throw new Error("Unable to revoke reversed Premium entitlement");
      }
      const revokedRows = await revokeResponse.json();
      return json({
        received: true,
        reconciled: true,
        capture_reversed: true,
        entitlement_revoked: Array.isArray(revokedRows) && revokedRows.length > 0,
      });
    }

    // One-time Premium purchases use Orders API captures, not subscription
    // sales. PAYMENT.CAPTURE.REFUNDED identifies the refund resource; resolve
    // its parent capture through PayPal's verified refund record before lookup.
    if (eventType === "PAYMENT.CAPTURE.REFUNDED") {
      const refundId = String(resource.id || "").trim();
      if (!/^[A-Z0-9]{8,64}$/i.test(refundId)) {
        return json({ error: "Invalid PayPal refund identifier" }, 422);
      }
      const refundResponse = await fetch(
        baseUrl + "/v2/payments/refunds/" + encodeURIComponent(refundId),
        { headers: { Authorization: "Bearer " + token, Accept: "application/json" } },
      );
      if (!refundResponse.ok) {
        throw new Error("Unable to verify PayPal refund");
      }
      const refund = await refundResponse.json();
      const refundAmount = refund.amount || {};
      if (refund.id !== refundId ||
          String(refund.status || "").toUpperCase() !== "COMPLETED" ||
          String(refundAmount.currency_code || "").toUpperCase() !== "EUR" ||
          !Number.isFinite(Number(refundAmount.value)) ||
          Number(refundAmount.value) <= 0) {
        return json({ error: "PayPal refund validation failed" }, 403);
      }
      const refundLinks = Array.isArray(refund.links) ? refund.links : [];
      const parentLink = refundLinks.find((link: Record<string, unknown>) =>
        String(link.rel || "").toLowerCase() === "up"
      );
      let captureId = "";
      try {
        const parentUrl = new URL(String(parentLink?.href || ""));
        const captureMatch = parentUrl.pathname.match(/^\/v2\/payments\/captures\/([A-Z0-9]{8,64})$/i);
        if (parentUrl.origin === new URL(baseUrl).origin && captureMatch) {
          captureId = captureMatch[1];
        }
      } catch (_error) {
        captureId = "";
      }
      if (!captureId) {
        return json({ error: "PayPal refund parent capture is invalid" }, 422);
      }
      const captureResponse = await fetch(
        baseUrl + "/v2/payments/captures/" + encodeURIComponent(captureId),
        { headers: { Authorization: "Bearer " + token, Accept: "application/json" } },
      );
      if (!captureResponse.ok) {
        throw new Error("Unable to verify refunded PayPal capture");
      }
      const capture = await captureResponse.json();
      const captureStatus = String(capture.status || "").toUpperCase();
      if (capture.id !== captureId ||
          !new Set(["PARTIALLY_REFUNDED", "REFUNDED"]).has(captureStatus)) {
        return json({ error: "PayPal capture refund status validation failed" }, 403);
      }
      const captureAmount = capture.amount || {};
      if (String(captureAmount.currency_code || "").toUpperCase() !== "EUR" ||
          !Number.isFinite(Number(captureAmount.value)) ||
          Number(captureAmount.value) <= 0) {
        return json({ error: "PayPal capture amount validation failed" }, 422);
      }
      const ledgerResponse = await fetch(
        supabaseUrl + "/rest/v1/sowia_financial_transactions" +
          "?provider=eq.paypal&transaction_type=eq.payment&provider_payment_id=eq." +
          encodeURIComponent(captureId) +
          "&select=user_id,paypal_order_id,gross_amount,gross_currency&limit=1",
        { headers: {
          apikey: serviceRoleKey,
          Authorization: "Bearer " + serviceRoleKey,
          Accept: "application/json",
        } },
      );
      if (!ledgerResponse.ok) {
        throw new Error("Unable to locate PayPal capture ownership");
      }
      const ledgerRows = await ledgerResponse.json();
      const ledger = Array.isArray(ledgerRows) && ledgerRows.length === 1
        ? ledgerRows[0]
        : null;
      const uuidPattern =
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
      const orderId = String(capture.supplementary_data?.related_ids?.order_id || "").trim();
      if (!ledger || !uuidPattern.test(String(ledger.user_id || "")) ||
          !ledger.paypal_order_id || ledger.paypal_order_id !== orderId ||
          Number(ledger.gross_amount) !== Number(captureAmount.value) ||
          String(ledger.gross_currency || "").toUpperCase() !== "EUR") {
        return json({ error: "PayPal capture ownership or order validation failed" }, 403);
      }
      const refundEventTime = String(event.create_time || "").trim();
      if (!refundEventTime || !Number.isFinite(Date.parse(refundEventTime))) {
        return json({ error: "PayPal refund event timestamp is invalid" }, 422);
      }

      // Persist the verified refund in the immutable financial ledger.
      // The capture-row lock in the database trigger serializes concurrent
      // refunds and prevents cumulative refunds from exceeding the capture.
      const refundLedgerUrl = supabaseUrl +
        "/rest/v1/sowia_financial_transactions?provider=eq.paypal" +
        "&transaction_type=eq.refund&provider_payment_id=eq." +
        encodeURIComponent(refundId) +
        "&select=user_id,parent_capture_id,gross_amount,gross_currency,status&limit=1";
      const refundLedgerHeaders = {
        apikey: serviceRoleKey,
        Authorization: "Bearer " + serviceRoleKey,
        Accept: "application/json",
      };
      const existingRefundResponse = await fetch(refundLedgerUrl, {
        headers: refundLedgerHeaders,
      });
      if (!existingRefundResponse.ok) {
        throw new Error("Unable to check PayPal refund ledger idempotency");
      }
      const existingRefundRows = await existingRefundResponse.json();
      const existingRefund = Array.isArray(existingRefundRows) &&
          existingRefundRows.length === 1
        ? existingRefundRows[0]
        : null;
      const refundLedgerMatches = (row: Record<string, unknown>) =>
        String(row.user_id || "") === String(ledger.user_id) &&
        String(row.parent_capture_id || "") === captureId &&
        Number(row.gross_amount) === Number(refundAmount.value) &&
        String(row.gross_currency || "").toUpperCase() === "EUR" &&
        String(row.status || "") === "manual_review";
      if (existingRefund && !refundLedgerMatches(existingRefund)) {
        return json({ error: "Existing PayPal refund ledger entry conflicts with verified refund" }, 409);
      }
      if (!existingRefund) {
        const insertRefundResponse = await fetch(
          supabaseUrl + "/rest/v1/sowia_financial_transactions?on_conflict=provider,provider_payment_id,transaction_type",
          {
            method: "POST",
            headers: {
              ...refundLedgerHeaders,
              "Content-Type": "application/json",
              Prefer: "resolution=ignore-duplicates,return=minimal",
            },
            body: JSON.stringify({
              user_id: String(ledger.user_id),
              provider: "paypal",
              provider_payment_id: refundId,
              parent_capture_id: captureId,
              transaction_type: "refund",
              status: "manual_review",
              gross_amount: Number(refundAmount.value),
              gross_currency: "EUR",
              occurred_at: refundEventTime,
            }),
          },
        );
        if (!insertRefundResponse.ok) {
          console.error("PayPal refund ledger insert failed", await insertRefundResponse.text());
          throw new Error("Unable to persist verified PayPal refund");
        }
        // A concurrent duplicate may win the unique constraint first. Re-read
        // the row and require exact identity rather than assuming the conflict
        // was harmless.
        const confirmRefundResponse = await fetch(refundLedgerUrl, {
          headers: refundLedgerHeaders,
        });
        if (!confirmRefundResponse.ok) {
          throw new Error("Unable to confirm PayPal refund ledger entry");
        }
        const confirmedRefundRows = await confirmRefundResponse.json();
        const confirmedRefund = Array.isArray(confirmedRefundRows) &&
            confirmedRefundRows.length === 1
          ? confirmedRefundRows[0]
          : null;
        if (!confirmedRefund || !refundLedgerMatches(confirmedRefund)) {
          return json({ error: "PayPal refund ledger confirmation failed" }, 409);
        }
      }

      const revokeResponse = await fetch(
        supabaseUrl + "/rest/v1/sowia_entitlements?user_id=eq." +
          encodeURIComponent(String(ledger.user_id)) + "&paypal_order_id=eq." +
          encodeURIComponent(orderId) + "&status=eq.active",
        { method: "PATCH", headers: {
          apikey: serviceRoleKey,
          Authorization: "Bearer " + serviceRoleKey,
          "Content-Type": "application/json",
          Prefer: "return=representation",
        }, body: JSON.stringify({ status: "inactive" }) },
      );
      if (!revokeResponse.ok) {
        throw new Error("Unable to revoke refunded Premium entitlement");
      }
      const revokedRows = await revokeResponse.json();
      return json({
        received: true,
        reconciled: true,
        entitlement_revoked: Array.isArray(revokedRows) && revokedRows.length > 0,
      });
    }
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

    const normalizedStatus = String(subscription.status || "").toUpperCase();
    const allowedStatuses = new Set([
      "APPROVAL_PENDING",
      "APPROVED",
      "ACTIVE",
      "SUSPENDED",
      "CANCELLED",
      "EXPIRED",
    ]);
    if (!allowedStatuses.has(normalizedStatus)) {
      return json({ error: "Unsupported PayPal subscription status" }, 422);
    }

    const billing = subscription.billing_info || {};
    const failedPaymentsCount = Number(billing.failed_payments_count);
    if (!Number.isInteger(failedPaymentsCount) || failedPaymentsCount < 0) {
      return json({ error: "PayPal failed-payment counter is invalid" }, 422);
    }
    // PayPal keeps a subscription ACTIVE while retrying failed charges.
    // Do not grant Premium during that retry window; PayPal resets this
    // consecutive-failure counter to zero after a successful payment.
    let effectiveStatus = normalizedStatus === "ACTIVE" && failedPaymentsCount > 0
      ? "past_due"
      : normalizedStatus.toLowerCase();

    // Signed terminal/suspension events are authoritative. A GET immediately
    // after webhook delivery can briefly lag the event; never let that stale
    // snapshot turn a cancelled/expired subscription back into active access.
    if (eventType === "BILLING.SUBSCRIPTION.CANCELLED") {
      effectiveStatus = "cancelled";
    } else if (eventType === "BILLING.SUBSCRIPTION.EXPIRED") {
      effectiveStatus = "expired";
    } else if (eventType === "BILLING.SUBSCRIPTION.SUSPENDED") {
      effectiveStatus = "suspended";
    }

    // The database RPC serializes state transitions under a transaction lock.
    // This prevents simultaneous refund and recovery notifications from
    // overwriting payment_review based on stale reads.
    const verifiedPaymentRecovery =
      eventType === "BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED" &&
      normalizedStatus === "ACTIVE" && failedPaymentsCount === 0;
    const lastPayment = billing.last_payment || {};
    const paymentAmount = lastPayment.amount || {};
    if (paymentAmount.value !== undefined &&
        (Number(paymentAmount.value) !== 9.90 ||
         String(paymentAmount.currency_code || "").toUpperCase() !== "EUR")) {
      return json({ error: "PayPal last payment amount mismatch" }, 403);
    }
    // A successful retry must carry an independently verifiable latest
    // payment amount, currency and timestamp. An ACTIVE subscription and a
    // zero failure counter alone are not sufficient to release a refund hold.
    if (verifiedPaymentRecovery) {
      const lastPaymentTime = String(lastPayment.time || "").trim();
      if (Number(paymentAmount.value) !== 9.90 ||
          String(paymentAmount.currency_code || "").toUpperCase() !== "EUR" ||
          !lastPaymentTime || !Number.isFinite(Date.parse(lastPaymentTime))) {
        return json({ error: "PayPal recovery payment proof is incomplete" }, 403);
      }
    }

    const eventTime = String(event.create_time || "").trim();
    if (!eventTime || !Number.isFinite(Date.parse(eventTime))) {
      return json({ error: "PayPal event timestamp is invalid" }, 422);
    }

    const eventId = String(event.id || "").trim();
    if (!eventId || eventId.length > 128) {
      return json({ error: "PayPal event identifier is invalid" }, 422);
    }

    const reconcileResponse = await fetch(
      supabaseUrl + "/rest/v1/rpc/sowia_reconcile_paypal_subscription",
      {
        method: "POST",
        headers: {
          apikey: serviceRoleKey,
          Authorization: "Bearer " + serviceRoleKey,
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          p_user_id: userId,
          p_paypal_subscription_id: subscriptionId,
          p_paypal_plan_id: planId,
          p_event_type: eventType,
          p_status: effectiveStatus,
          p_currency: paymentAmount.currency_code || null,
          p_amount: paymentAmount.value === undefined
            ? null
            : Number(paymentAmount.value),
          p_next_billing_time: billing.next_billing_time || null,
          p_last_payment_at: lastPayment.time || null,
          p_event_time: eventTime,
          p_event_id: eventId,
          p_recovery_verified: verifiedPaymentRecovery,
        }),
      },
    );
    if (!reconcileResponse.ok) {
      console.error(
        "Supabase atomic subscription reconciliation failed",
        await reconcileResponse.text(),
      );
      throw new Error("Unable to persist subscription state");
    }
    const reconciledStatus = await reconcileResponse.json();
    return json({
      received: true,
      reconciled: true,
      status: reconciledStatus,
    });
  } catch (error) {
    console.error("PayPal webhook handler error", error);
    return json({ error: "Webhook processing failed" }, 500);
  }
});
