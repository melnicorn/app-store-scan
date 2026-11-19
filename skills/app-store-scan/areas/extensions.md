# extensions: app extensions, widgets, App Clips, Siri and Shortcuts

Guidelines 4.4, 2.5.11, 2.5.12, 2.5.16, 2.5.18, 4.5.3. Applies when the project has extension targets, an App Clip, a watch app, or uses Intents/App Intents, WidgetKit, ActivityKit or CallKit. Report only checks for extension types that exist. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**EXT-01** `[all]` (2.5.16, 4.4 · high) Every extension, widget and notification relates to the app's content and function, and the containing app has real functionality of its own (at least help and settings for the extension). Extensions are disclosed accurately in marketing text.

**EXT-02** `[all]` (4.4, 2.5.18 · blocker) No marketing, advertising or in-app purchases inside extensions. Display ads belong only in the main app binary: not in widgets, App Clips, keyboards, notification content, Live Activities or watchOS apps.

**EXT-03** `[ios]` (4.4.1 · blocker) Keyboard extensions provide actual text input, include a next-keyboard control (`handleInputModeList` / globe key), stay functional without network access and without Full Access (`RequestsOpenAccess`), collect user activity only to improve the keyboard on device, do not launch other apps except Settings, and do not repurpose keys.

**EXT-04** `[all]` (4.4.2 · high) Safari extensions run on the current Safari, do not interfere with Safari or system UI, contain no misleading code, and request access to no more sites than they need (check `manifest.json` host permissions and `SFSafariWebsiteAccess`; `<all_urls>` needs a reason).

**EXT-05** `[ios]` (2.5.16(a) · high) App Clips: every App Clip feature also exists in the full app; no advertising; the clip is useful immediately without sign-up walls; size and entitlement limits are respected.

**EXT-06** `[all]` (2.5.11 · high) Siri and Shortcuts: register only intents the app can fulfil itself and that users would expect from its stated function; vocabulary and phrases relate to the app (no generic terms, no third-party names); requests are resolved directly with no ads or marketing in between. Check `AppShortcutsProvider` phrases and intent definitions.

**EXT-07** `[ios]` (2.5.12 · high) CallKit and SMS/call filtering extensions block only confirmed spam numbers, explain their criteria in marketing text, and do not use the data for tracking, profiling or sale.

**EXT-08** `[all]` (4.5.3, 4.5.4 · high) Widgets, Live Activities and notification extensions are not used for promotions or unsolicited messages; Live Activities represent an actual ongoing task or event.

**EXT-09** `[all]` (upload · high) Extension plumbing: each extension's bundle id is prefixed by the containing app's bundle id; versions match the app; each has its own purpose strings and privacy manifest entries for the APIs it uses; app groups in entitlements match between app and extension.
