# technical: software requirements

Guidelines 2.4 and 2.5. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**TECH-01** `[all]` (2.5.1 · blocker) Public APIs only. Follow `private_api`: selectors or classes built from strings that name underscore-prefixed or undocumented symbols, `dlopen`/`dlsym` of system frameworks, anything under `PrivateFrameworks`, KVC on private keys (`value(forKey: "_...")`), method swizzling of system classes. `NSClassFromString`/`performSelector` on your own or public symbols is fine. Check vendored binaries' names against known private-API users if any stand out.

**TECH-02** `[all]` (2.5.1 · blocker) No removed or deprecated technology. `UIWebView` anywhere, including inside old SDKs, fails upload (ITMS-90809). Also flag OpenGL ES-only rendering, `AddressBook`, `ALAssetsLibrary` and similar long-deprecated frameworks as medium.

**TECH-03** `[all]` (2.5.2 · blocker) No downloaded code that changes features. Follow `dynamic_code`. Fail: native code or frameworks fetched at runtime; scripts downloaded and executed to add or alter features; remote switches that turn the app into something App Review did not see. Allowed: JavaScript run inside WebKit/JavaScriptCore that does not change the app's primary purpose; over-the-air updates of interpreted JS (CodePush, Expo Updates) limited to fixes and content consistent with the reviewed app: report those as `warn` (medium) with the constraint spelled out. Educational coding apps may download code only if the source is fully viewable and editable.

**TECH-04** `[ios]` (2.5.4 · high) Background modes are each used by a visible feature. For every entry in `UIBackgroundModes` find the code that needs it: `audio` needs real audible playback or recording; `location` needs a continuous-location feature the user started; `voip` needs CallKit calls; `fetch`/`processing` need `BGTaskScheduler` work. Fail for a mode with no matching feature, or one used as a keep-alive (silent audio, location to stay running).

**TECH-05** `[all]` (2.5.5 · high) Works on IPv6-only networks. Follow `ipv4_only`: hardcoded IPv4 literals for servers, `AF_INET`-only sockets, `gethostbyname`, `inet_addr`, IPv4-only address types in networking code that ships in the app. Review tests on an IPv6-only NAT64 network. Hostnames with `URLSession`/`Network.framework` are fine. Purely local-network features (talking to a device on the user's LAN by IPv4) are a common, usually accepted exception: report as `warn` (medium), say the reviewer network has no such device, and point to check COMP-09 in the `completeness` area (reviewer access). Internet-facing IPv4-only code is a fail.

**TECH-06** `[ios]` (2.5.6 · high) Web browsing uses WebKit. Apps that browse the web must use `WKWebView`/`SFSafariViewController` (alternative engines need an entitlement, EU/Japan only). Bundled Chromium, GeckoView or a custom engine fails.

**TECH-07** `[all]` (2.5.19, 2.3.1 · blocker) No hidden, dormant or undocumented features. Follow `hidden_features`. Fail: code paths that behave differently for reviewers (checks on review status, date gates, geofences around Cupertino, build-number gates), features unlocked by secret gestures or codes, server flags whose purpose is to enable something after approval. Ordinary feature flags and A/B tests are fine: `warn` (low) only when a flag gates a whole feature that review would not see, and say it must be on and described in the review notes.

**TECH-08** `[all]` (2.4.2 · high) Reasonable resource use. Fail on on-device crypto mining (also 3.1.5(ii)), deliberate keep-awake abuse, or unbounded background work. `isIdleTimerDisabled` for an app that is meant to stay on screen (dashboard, navigation, video) is fine; mention it only if it is set unconditionally and never restored.

**TECH-09** `[all]` (2.4.4, 2.5.8, 2.5.9 · high) Respects the system. Fail when the app tells users to restart the device or change unrelated system settings (turn off Wi-Fi, disable security features), deep-links into private Settings URLs (`App-Prefs:`, `prefs:root`), repurposes volume or ring/silent switches, blocks expected system behaviors, or presents an alternate home screen. `UIApplication.openSettingsURLString` is fine.

**TECH-10** `[all]` (2.5.1, 2.5.13, 2.5.15, 2.5.17 · medium) Frameworks used for their purpose. HealthKit only for health and fitness, HomeKit only for home automation, each mentioned in the description. Face authentication uses LocalAuthentication, not ARKit or custom face recognition. File pickers include Files and iCloud documents (`UIDocumentPickerViewController` / `fileImporter`), not only a private directory listing. Matter pairing goes through Apple's Matter support framework.

**TECH-11** `[ios]` (2.4.1 · medium) Runs on iPad. iPhone apps should run on iPad; review runs iPhone-only apps on iPad in compatibility mode, so layouts must not break there. If the target is iPhone-only, warn (low). If it is universal, check for layouts that assume one size class or orientation, and that `UIRequiredDeviceCapabilities` does not exclude devices the app could support.

**TECH-13** `[all]` (2.4.2, 5.1.1 · medium) Local-network discovery is restrained. Prefer Bonjour or a user-entered address over sweeping the subnet. Flag repeated broadcast or per-address probing of the whole LAN on a short timer: it drains battery, looks like network scanning, and should back off or stop once a device is found.

**TECH-12** `[all]` (2.5.3, 1.6 · high) Nothing that harms the system or user data: no code that probes, exploits or disrupts the OS, other apps, push or Game Center; no transmission of executable payloads. Rare; report only on real evidence.
