# privacy: data collection, use and sharing

Guidelines 5.1.1, 5.1.2, 1.6. Technical permission plumbing is in `permissions`; this area is about what data leaves the device and whether users were told. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

Start by building a short data map from the signals: what the app collects (accounts, content, identifiers, usage, location, files), where each item goes (own server, named SDKs, AI providers), and whether anything leaves the device at all. Put that map in the area `summary`. An app that sends nothing off the device passes most of this area quickly; say so.

**PRIV-01** `[all]` (5.1.1(i) · high) Privacy policy reachable inside the app. Every app needs a privacy policy URL in App Store Connect (manual) and an easily found link in the app itself (settings, about, sign-up, paywall). Fail when the app collects any user data and has no in-app link. If the app collects nothing, a missing in-app link is a `warn` (low): a policy URL is still mandatory in App Store Connect, and the policy must say what is and is not collected, name third parties, and explain retention and deletion.

**PRIV-02** `[all]` (5.1.1(ii) · high) Consent before collection, and a way to withdraw it. Analytics, crash reporting with identifiers, and any personal data need user consent, even when "anonymous". Fail when collection starts at launch with no disclosure for non-essential data, or when there is no opt-out where the law or the SDK expects one. Paid features must not depend on agreeing to data collection.

**PRIV-03** `[all]` (5.1.2(i) · blocker) Sharing with third parties, including third-party AI, is disclosed and explicitly permitted. Follow `third_party_ai`, `analytics_sdk` and `network_calls`. If user content, prompts, photos, voice, contacts or identifiers are sent to an AI provider or any other third party, the app must say who receives it and get explicit permission first (a clear consent screen naming the provider, not just a line in the policy). Fail when personal data goes to a third-party AI service with no in-app disclosure and consent step.

**PRIV-04** `[all]` (2.3, 5.1.1 · high, mostly manual) App Privacy answers match reality. From the data map and SDK list, state which App Privacy ("nutrition label") data types the developer will have to declare (contact info, identifiers, usage data, diagnostics, location, user content, and whether each is linked to identity or used for tracking), including what SDKs collect. Report as `manual` with that list. Fail only if a checked-in privacy manifest's `NSPrivacyCollectedDataTypes` plainly contradicts the code.

**PRIV-05** `[all]` (5.1.1(iii),(v),(x) · high) Data minimization. The app may not require personal information that is not needed for its core function: no mandatory phone number, birthdate, gender, address or contacts upload unless the feature needs it or the law requires it. Optional requests for name and email are fine if features do not depend on them.

**PRIV-06** `[all]` (5.1.2(iv),(v) · high) Contacts and photos are not harvested. No uploading the address book to build a contact database; no messaging the user's contacts except one at a time at the user's explicit initiative, with no "select all" and a preview of the message. No collecting the list of installed apps (`canOpenURL` probing of many schemes, large `LSApplicationQueriesSchemes`) for analytics or ads.

**PRIV-07** `[all]` (5.1.2(ii),(iii) · high) No repurposing, profiling or fingerprinting. Data collected for one purpose is not reused for another without consent. No combining device signals (model, fonts, locale, disk size, boot time, IDFV plus IP) into an identifier; no attempts to re-identify anonymized data.

**PRIV-08** `[all]` (5.1.2(vi), 5.1.2(vii) · blocker) Sensitive-API data is never used for ads or data mining: HealthKit, HomeKit, ClassKit, face/depth data from ARKit or the camera, Clinical Records, Apple Pay data. Check that such data is not passed to analytics or ad SDKs.

**PRIV-09** `[all]` (5.1.1(vi)-(viii) · blocker) No surreptitious collection. No capturing passwords or private data from web views (injected JavaScript reading form fields, keylogging), no hidden or zero-size `SFSafariViewController` used for cookie syncing, no compiling personal information about people from public sources without their consent.

**PRIV-10** `[all]` (1.6 · medium) Stored and transmitted securely. Tokens, passwords and keys belong in the Keychain, not `UserDefaults`, plist files or plain files (`insecure_storage` signal). Personal data goes over TLS. Sensitive files should use data protection. Report concrete instances only.

**PRIV-11** `[all]` (5.1.1(i) · medium, manual) Data deletion and retention are described. If the app stores user data on a server, the user must be able to request deletion (account deletion is checked in `accounts`) and the policy must describe retention. For local-only apps: `na`.
