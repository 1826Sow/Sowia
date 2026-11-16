// One-time SOW IA Premium checkout. Requires a valid Supabase user JWT.
// PayPal credentials and the Supabase service-role key remain Edge Function secrets.
const corsHeaders = {
  "Access-Control-Allow-Origin": "https://fm5aczcvvj5jgkhpxwqtcr.streamlit.app",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Vary": "Origin",
};

const PRICE = "9.90";
const CURRENCY = "EUR";
const APP_URL = "https://fm5aczcvvj5jgkhpxwqtcr.streamlit.app";

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function env(name: string): string {
  const value = Deno.env.get(name)?.trim();
  if (!value) throw new Error("Missing Edge Function secret: " + name);
  return value;
}

async function paypalToken(base: string, clientId: string, secret: string) {
  const response = await fetch(base + "/v1/oauth2/token", {
    method: "POST",
    headers: {
      Authorization: "Basic " + btoa(clientId + ":" + secret),
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: "grant_type=client_credentials",
  });
  if (!response.ok) throw new Error("PayPal authentication failed");
  const payload = await response.json();
  if (!payload.access_token) throw new Error("PayPal access token missing");
  return String(payload.access_token);
}

async function paypalRequest(base: string, token: string, path: string, init: RequestInit = {}) {
  const response = await fetch(base + path, {
    ...init,
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(init.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    console.error("PayPal API error", response.status);
    throw new Error("PayPal request failed");
  }
  return body;
}

async function validateOrder(order: any, orderId: string, userId: string) {
  const units = Array.isArray(order?.purchase_units) ? order.purchase_units : [];
  if (
    order?.id !== orderId ||
    order?.intent !== "CAPTURE" ||
    !["APPROVED", "COMPLETED"].includes(String(order?.status || "")) ||
    units.length !== 1
  ) return false;

  const unit = units[0];
  return unit?.reference_id === "sowia-premium" &&
    unit?.custom_id === userId &&
    unit?.amount?.currency_code === CURRENCY &&
    unit?.amount?.value === PRICE;
}

function validateCapture(order: any, orderId: string) {
  const captures = order?.purchase_units?.[0]?.payments?.captures;
  if (order?.id !== orderId || order?.status !== "COMPLETED" ||
      !Array.isArray(captures) || captures.length !== 1) return null;
  const capture = captures[0];
  if (!capture?.id || capture.status !== "COMPLETED" ||
      capture.amount?.currency_code !== CURRENCY ||
      capture.amount?.value !== PRICE) return null;
  return capture;
}

Deno.serve(async (req: Request) => {
  const origin = req.headers.get("origin");
  if (req.method === "OPTIONS") {
    if (origin && origin !== APP_URL) return new Response("Forbidden", { status: 403 });
    return new Response("ok", { headers: corsHeaders });
  }
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);
  if (origin && origin !== APP_URL) return json({ error: "Origin not allowed" }, 403);

  try {
    const authorization = req.headers.get("authorization") || "";
    const match = authorization.match(/^Bearer\s+(.+)$/i);
    if (!match) return json({ error: "Authentication required" }, 401);
    const userJwt = match[1];

    const supabaseUrl = env("SUPABASE_URL").replace(/\/$/, "");
    const serviceRole = env("SUPABASE_SERVICE_ROLE_KEY");
    const userResponse = await fetch(supabaseUrl + "/auth/v1/user", {
      headers: {
        apikey: serviceRole,
        Authorization: "Bearer " + userJwt,
      },
    });
    if (!userResponse.ok) return json({ error: "Invalid user session" }, 401);
    const user = await userResponse.json();
    const userId = String(user?.id || "");
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(userId)) {
      return json({ error: "Invalid user identity" }, 401);
    }

    const clientId = env("PAYPAL_CLIENT_ID");
    const clientSecret = env("PAYPAL_CLIENT_SECRET");
    const mode = (Deno.env.get("PAYPAL_MODE") || "sandbox").trim().toLowerCase();
    if (mode !== "sandbox") return json({ error: "Only Sandbox is enabled for this checkout" }, 503);
    const base = "https://api-m.sandbox.paypal.com";
    const token = await paypalToken(base, clientId, clientSecret);
    const input = await req.json().catch(() => ({}));
    const action = String(input?.action || "");

    if (action === "create") {
      const order = await paypalRequest(base, token, "/v2/checkout/orders", {
        method: "POST",
        headers: { "PayPal-Request-Id": crypto.randomUUID() },
        body: JSON.stringify({
          intent: "CAPTURE",
          purchase_units: [{
            reference_id: "sowia-premium",
            custom_id: userId,
            description: "Accès Premium SOW IA",
            amount: { currency_code: CURRENCY, value: PRICE },
          }],
          payment_source: {
            paypal: {
              experience_context: {
                return_url: APP_URL,
                cancel_url: APP_URL + "/?paypal=cancel",
                user_action: "PAY_NOW",
              },
            },
          },
        }),
      });
      const approval = (order.links || []).find((link: any) =>
        ["approve", "payer-action"].includes(link.rel)
      )?.href;
      if (!order.id || !approval) return json({ error: "PayPal approval link missing" }, 502);
      return json({ order_id: order.id, approval_url: approval });
    }

    if (action === "capture") {
      const orderId = String(input?.order_id || "").trim();
      if (!/^[A-Z0-9]{1,50}$/.test(orderId)) return json({ error: "Invalid order ID" }, 400);

      const existing = await paypalRequest(base, token, "/v2/checkout/orders/" + encodeURIComponent(orderId));
      if (!await validateOrder(existing, orderId, userId)) {
        return json({ error: "Order does not belong to this account or price" }, 403);
      }

      let completed = existing;
      if (existing.status !== "COMPLETED") {
        completed = await paypalRequest(base, token, "/v2/checkout/orders/" + encodeURIComponent(orderId) + "/capture", {
          method: "POST",
          headers: { "PayPal-Request-Id": "sowia-premium-capture-" + orderId },
          body: "{}",
        });
      }

      const capture = validateCapture(completed, orderId);
      if (!capture) return json({ error: "Payment capture is not completed or does not match" }, 402);

      const entitlementResponse = await fetch(
        supabaseUrl + "/rest/v1/sowia_entitlements?on_conflict=user_id",
        {
          method: "POST",
          headers: {
            apikey: serviceRole,
            Authorization: "Bearer " + serviceRole,
            "Content-Type": "application/json",
            Prefer: "resolution=merge-duplicates,return=minimal",
          },
          body: JSON.stringify({
            user_id: userId,
            plan: "premium",
            status: "active",
            provider: "paypal",
            paypal_access_blocked: false,
            paypal_order_id: orderId,
            amount: PRICE,
            currency: CURRENCY,
            updated_at: new Date().toISOString(),
          }),
        },
      );
      if (!entitlementResponse.ok) {
        console.error("Supabase entitlement write failed", entitlementResponse.status);
        return json({ error: "Payment confirmed but entitlement recording failed; contact support" }, 503);
      }
      return json({ status: "COMPLETED", order_id: orderId, capture_id: capture.id });
    }

    return json({ error: "Unsupported action" }, 400);
  } catch (error) {
    console.error("One-time PayPal checkout failed", error);
    return json({ error: "Checkout could not be completed" }, 500);
  }
});
