# design: minimum functionality, Apple services, ads, prompts

Guidelines 4.2, 4.3, 4.5, 4.10, 2.5.18, 3.2.2, 5.6.1. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**DES-01** `[all]` (4.2 · high) More than a website or a thin shell. Fail when the app is essentially one web view onto a site, a set of links, a single piece of content, or marketing material. Look at the root view and navigation: is there native UI and functionality that would not exist in Safari? Hybrid apps (Capacitor, Cordova, a `WKWebView` root) need native-feeling features: offline behavior, native navigation, system integrations. Judge usefulness too: an app with one trivial function is a 4.2 risk.

**DES-02** `[all]` (4.3, 4.2.6 · high) Not spam. Risky: generated from a commercial template or app builder and submitted by someone other than the content owner; one of several near-identical apps differing by content or region (use one app with in-app selection); a new entry in a saturated low-effort category (flashlight, wallpaper, fortune telling, simple timer, sound effects, dating clone) with nothing distinctive. Look for template residue: default names, generic bundle ids, white-label config switching brand per build.

**DES-03** `[all]` (4.2.3 · medium) Stands alone. The app must work without another app installed. If it downloads substantial resources on first launch, it must state the size and ask first. An app that needs separate hardware or companion software to do anything must say so clearly on first launch and in its listing, and still present a usable, explained state without it. The in-app state decides the status; what the listing must say goes in `fix`. See also COMP-09 in `completeness`.

**DES-04** `[all]` (4.5.4, 4.5.3 · high) Push used properly. The app must function with notifications declined. Marketing or promotional pushes need explicit in-app opt-in and an in-app opt-out. No sensitive personal information in pushes; no spam through push, Game Center or Live Activities. Follow `push`: where is permission requested, and does anything break when denied?

**DES-05** `[all]` (5.6.1, 3.2.2(x) · high) Ratings and reviews. Review prompts must use the system API (`requestReview`); custom prompts that ask for stars and then route unhappy users elsewhere, or that link out to write a review as the main prompt, are disallowed. Never require or reward a rating, review, or other-app download for access. Follow `custom_review_prompt`, `review_prompt_api`, `forced_actions`.

**DES-06** `[all]` (2.5.18, 3.2.2(iii) · high) Advertising. Ads only in the main app binary, appropriate for the age rating, with a visible close/skip control on interstitials, clearly labeled as ads, and a way to report inappropriate ads. No targeting based on health, school or kids data. An app that exists mainly to show ads, or that inflates impressions or clicks, fails. No ad SDK: `na`.

**DES-07** `[all]` (4.5.1, 4.5.2, 4.5.5 · high) Apple sites and services. No scraping Apple sites or building rankings from them (approved RSS feeds and the iTunes Search API for the app's own lookup are fine). MusicKit: user-initiated playback with standard controls, no charging for or monetizing Apple Music access, no saving or sharing its audio. Game Center player IDs are never displayed or shared.

**DES-08** `[all]` (4.10 · high) No charging for built-in capabilities. Push, camera, gyroscope, iCloud storage, Apple Music access or Screen Time APIs may not be the thing a purchase unlocks.

**DES-09** `[all]` (3.2.2(v), 3.2.2(i) · medium) No arbitrary restrictions (blocking users by carrier or location without a legal or functional reason) and no store-like catalog of third-party apps. Follow `geo_restriction`.

**DES-10** `[all]` (4.2.1 · medium) ARKit apps offer a real AR experience, not a single model dropped into a camera view. No ARKit: `na`.

**DES-11** `[all]` (4, HIG · low) Platform fit. Only report clear problems a reviewer would notice in the first minute: UI clipped by the notch, home indicator or Dynamic Island; no iPad or landscape handling in a universal app; unreadable in Dark Mode; controls too small to tap; non-standard back or dismiss behavior; sign-up pushed out to an external browser. Keep to what the code makes evident.
