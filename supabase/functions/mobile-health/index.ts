import "jsr:@supabase/functions-js/edge-runtime.d.ts";

// This endpoint is intentionally minimal. Supabase's platform-level JWT
// verification is enabled for this function; callers must send a user access
// token in Authorization: Bearer <JWT>. It does not accept API keys as tokens.
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
};

function json(status: number, body: Record<string, unknown>): Response {
  return new Response(JSON.stringify(body), { status, headers: corsHeaders });
}

Deno.serve((req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { status: 200, headers: corsHeaders });
  }

  if (req.method !== "GET") {
    return json(405, { ok: false, code: "METHOD_NOT_ALLOWED" });
  }

  // With verify_jwt enabled, the Supabase gateway rejects missing or invalid
  // JWTs before this handler runs. Never echo the bearer token or trust a
  // user ID supplied by the client.
  const authorization = req.headers.get("Authorization") ?? "";
  if (!authorization.startsWith("Bearer ")) {
    return json(401, { ok: false, code: "AUTH_REQUIRED" });
  }

  return json(200, {
    ok: true,
    service: "sowia-mobile-health",
    authenticated: true,
    contractVersion: 1,
  });
});
