export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/wake") {
      const headers = {
        "Cache-Control": "no-store, max-age=0",
        "Pragma": "no-cache",
      };

      try {
        // A user-initiated readiness check wakes the free Render service when idle.
        const upstream = await fetch("https://sowia.onrender.com/_stcore/health", {
          headers: { "Cache-Control": "no-cache", "Pragma": "no-cache" },
        });
        const body = await upstream.text();
        const ready = upstream.status === 200 && body.trim().toLowerCase() === "ok";
        return Response.json({ ready }, { headers });
      } catch {
        return Response.json({ ready: false }, { headers });
      }
    }

    return env.ASSETS.fetch(request);
  },
};
