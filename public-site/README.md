# SOW IA — public landing page

This directory contains a standalone, static discovery page. It does not import the Streamlit application, access Supabase, collect credentials, or weaken authentication.

## Preview locally

Open `index.html` in a browser. The language selector supports French, English and Spanish. The primary call to action points to the existing Streamlit application.

## Publishing

The page is intentionally isolated from the Streamlit deployment. Publishing it requires a separate static host (for example, GitHub Pages, Cloudflare Pages or an existing domain).

Before publishing:
1. Choose and configure the public domain and static host.
2. Confirm the destination application URL is still correct.
3. Add the final SOW IA visual identity assets supplied by the project owner. The current page uses CSS typography and simple glyphs only; it does not substitute a generated logo or crop the approved full mockup.
4. Add a canonical URL, social preview image and privacy/legal links once the final domain and policies are known.
5. Test mobile layout, all three languages, keyboard navigation and outbound sign-in flow on the published domain.

## Security boundary

- Keep `SOWIA_REQUIRE_AUTH=true` on the Streamlit application.
- Do not expose Supabase service-role keys or private application data on this page.
- Do not add analytics or tracking until the measurement plan and privacy notice are approved.
- The landing page describes only capabilities documented in the repository; optional services may require configuration.
