# SOW IA — Growth & Discovery

## Objective
Build a measurable acquisition and activation system that brings qualified visitors to SOW IA, helps them understand the platform before registration, and encourages repeat use and referrals.

This document is a product and go-to-market plan. It does not claim that any proposed feature is already implemented.

## Product principles
- Public discovery before account creation: explain the value and show verified demonstrations.
- Honest feature presentation: promote only capabilities verified as available in the deployed application.
- Mobile-first, accessible, fast-loading pages.
- Free-first acquisition; do not start paid campaigns until conversion tracking and messaging have been validated.
- Separate public marketing pages from authenticated workspaces and preserve existing application behavior.

## Visitor journey
1. Discovery: a social post, search result, partner link, or referral opens a public landing page.
2. Understanding: visitors see a short product demonstration, clear use cases, supported audiences, and transparent access/pricing information.
3. Trial: visitors can explore a safe public demo or create an account with a clear explanation of what happens next.
4. Activation: onboarding guides each new user to one useful first action (for example, ask the assistant, search the web, or create a document) only where that feature is verified and available.
5. Exploration: a guided directory explains personal, professional, business, and global areas without overwhelming new users.
6. Retention: saved work, a useful return prompt, help resources, and optional invitations encourage repeat visits.

## Public landing page requirements
- Responsive hero using approved SOW IA visual identity.
- Clear headline and concise value proposition.
- Full-width approved dashboard artwork shown without cropping or distortion where used as artwork; never use a static screenshot as a substitute for live controls.
- Short demonstration video or annotated product walkthrough.
- Feature cards with verified availability labels.
- Separate paths for individuals and professionals.
- Transparent registration, plan, privacy, and support information.
- Calls to action: “Découvrir SOW IA” and “Créer un compte”.
- Search-engine metadata, descriptive headings, social sharing previews, and language-ready content.

## Guided discovery inside the app
- Optional first-visit tour with skip and replay controls.
- A persistent “Découvrir SOW IA” entry point.
- Directory of application areas with plain-language descriptions and access requirements.
- Contextual next-step suggestions based on the current page, without exposing private user data.
- Clear empty states, help, and feedback route.

## Acquisition channels — initial free-first test
- TikTok, Instagram Reels, Facebook, and YouTube Shorts: practical 20–40 second demonstrations.
- LinkedIn: professional use cases, founder/organization stories, and product updates.
- Search: public pages targeting concrete user needs and tool use cases.
- Partnerships: creators, associations, entrepreneurs, training communities, and relevant organizations.
- Referral: shareable invitation links with transparent terms; no rewards until abuse prevention and terms are designed.

## Initial 30-day execution plan
### Week 1 — Foundation
- Verify current production features, access rules, pricing, and supported languages.
- Define landing-page copy and public/private route boundaries.
- Establish baseline analytics and privacy-conscious event definitions.

### Week 2 — Demonstration and discovery
- Publish the landing page and one short walkthrough after product claims are verified.
- Add onboarding prototype and guided directory in a separate feature branch.
- Prepare three audience-specific content themes: individuals, professionals, partners.

### Week 3 — Distribution
- Publish a consistent set of short demonstrations.
- Contact a small, relevant group of potential partners.
- Test referral sharing without financial incentives.

### Week 4 — Optimization
- Review acquisition and activation funnel.
- Identify where visitors leave or new users fail to complete a first useful action.
- Improve the highest-friction step; do not optimize for raw views alone.

## Measurement
Track aggregate, privacy-conscious metrics:
- Landing-page sessions and source/medium.
- CTA click-through rate.
- Registration starts and completed registrations.
- First successful meaningful action (activation).
- Repeat active users at 7 and 30 days.
- Referral shares and resulting activated registrations.
- Conversion by audience and acquisition channel.

Do not collect message contents or sensitive personal data for marketing analytics. Document consent, retention, and access controls before adding tracking.

## Release and safety gates
- Build in isolated feature branches and submit separate pull requests.
- Do not change protected `main` or deploy without explicit authorization.
- Verify mobile and desktop layouts, authentication boundaries, RLS, and existing critical workflows.
- Test that public visitors cannot access private documents, chat history, account details, or professional workspaces.
- Validate analytics events without recording sensitive content.
- Confirm all marketing claims against the deployed application before publication.

## Immediate next engineering milestone
Create a public-facing discovery experience and an in-app guided tour as a separate, independently reviewable implementation. First inspect the current routing, authentication, and page architecture; then propose the smallest safe implementation. No production changes are authorized by this plan alone.
