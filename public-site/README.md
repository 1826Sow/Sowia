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

## Audience measurement — approved direction

The project owner approved Cloudflare Web Analytics as the preferred visitor-measurement option. This is a preparation decision, not an active installation: the landing page has no public hostname or separate hosting deployment yet, and no Cloudflare site token has been supplied.

### What it can measure

- Page views and visitor/audience metrics shown in the Cloudflare Web Analytics dashboard.
- Performance measurements collected by the Cloudflare beacon.

Cloudflare Web Analytics does **not** currently support custom events. Do not promise or implement CTA/button-click counts with this beacon alone. If click-through measurement is later required, assess a separate privacy-reviewed method.

### Activation after hosting is chosen

1. Publish this static directory on the selected host and confirm the final public hostname.
2. Create a Cloudflare account/site entry for that hostname under Web Analytics.
3. If using Cloudflare Pages, enable Web Analytics in the Pages project's Metrics tab; Cloudflare says the beacon is added on the next deployment. Otherwise, copy the hostname-specific snippet from Manage site and add it before the closing `</body>` tag.
4. Verify that data appears in the Cloudflare dashboard and that the configured hostname matches the live site.
5. Add a clear privacy notice describing audience measurement and verify the provider's contractual and technical configuration against current CNIL requirements before relying on any consent exemption. Do not assume that a tool is automatically exempt merely because it is described as privacy-first.

Official references:
- [Cloudflare Web Analytics setup](https://developers.cloudflare.com/web-analytics/get-started/)
- [Cloudflare Web Analytics FAQ](https://developers.cloudflare.com/web-analytics/faq/)
- [CNIL — audience measurement solutions](https://www.cnil.fr/fr/cookies-solutions-pour-les-outils-de-mesure-daudience)

No tracking script, cookie banner, account identifier, or visitor-level profiling is added by this preparation change.
