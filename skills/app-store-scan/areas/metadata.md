# metadata: App Store listing

Guidelines 2.3, 1.5, 5.1.1(i). Most metadata lives in App Store Connect, not the repo. Check what is checked in (`fastlane/metadata`, `fastlane/screenshots`, README store copy, in-app strings) and turn the rest into a short, app-specific `manual` list. To keep the manual list short, META-03, META-06, META-09, META-10 and META-11 are folded: do not report them as separate checks unless this app has a specific exposure there (then report that one separately with app-specific text). Put their routine reminders into META-12's list instead. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**META-01** `[all]` (2.3.7 · blocker) Name, subtitle and keywords fit and are honest. Limits: name 30, subtitle 30, keywords 100 characters. No prices, "free", "best", "#1", other app names, or irrelevant trademarks. The name must be unique and match the on-device display name closely (2.3.8). Use the `metadata` fact and hints when a metadata directory exists; otherwise check `CFBundleDisplayName` and report the rest under META-12.

**META-02** `[all]` (2.3.7, 5.2.1, 4.1(c) · high) No third-party names or marks in the app name, icon or keywords without permission. An app that works with another company's product (a console, a game, a service, a car) may describe compatibility in the description ("for use with X") but should not lead its name or icon with that brand or imply it is official. If the display name, bundle name or icon contains someone else's product name, report a `warn` (high) at least, a `fail` if the app could be mistaken for the official app. Cross-reference `content` CONT-04.

**META-03** `[all]` (2.3.3, 2.3.4, 2.3.9 · high, manual) Screenshots and previews show the real app in use: not just a splash, login or marketing art; previews are screen captures only; no real people's data; rights held for everything shown. If screenshots are checked in, look at a couple.

**META-04** `[all]` (2.3.10 · high) No other platforms. The app and its metadata must not name or show Android, Google Play, other stores or other mobile platforms. Follow `other_platforms` in user-visible strings and bundled images or docs shown in-app. Mentions in comments or non-shipping code do not count.

**META-05** `[all]` (2.3.1, 2.3.2 · high) Listing matches the app. Description, screenshots and "What's New" must describe features that exist in this build, and say when featured content needs an in-app purchase. No claims the app cannot back up (virus scanning, health measurement, "official"). If checked-in copy promises something the code does not do, fail.

**META-06** `[all]` (2.3.6 · high, manual) Age rating answered honestly under the current questionnaire (updated 2026; includes in-app controls, capabilities, AI/chat, user-generated content, web access, gambling, medical). From the code, list the answers that are not "none": unrestricted web access, UGC or chat, AI assistant, mature themes, gambling, contests. Report as `manual` with that list.

**META-07** `[all]` (2.3.8 · high) Icons, screenshots and previews suit a 4+ audience even if the app is rated higher. "For Kids"/"For Children" wording is reserved for the Kids Category.

**META-08** `[all]` (1.5 · high) Contact is easy. The app and its Support URL need a working way to reach the developer. Look for a support or contact link in the app; if there is none, warn (medium). Support URL itself is manual.

**META-09** `[all]` (2.3.1(a), 2.3.12 · medium, manual) Review notes and What's New. Notes for Review must describe non-obvious features, hardware or network needs, sign-in details and in-app purchases specifically; generic notes are rejected. Draft the two or three sentences this app needs, based on what you saw.

**META-10** `[all]` (2.3.5 · low, manual) Category fits the app. Suggest the primary category that matches the code.

**META-11** `[all]` (2.3.11, 2.3.13, 2.3.14 · low) Pre-orders, in-app events and custom creative assets, if used, are accurate and not materially different from what ships. Usually `na`.

**META-12** `[all]` (2.1, 2.3 · manual) App Store Connect checklist. One `manual` check whose `fix` is a compact list of what must be filled in before submitting and cannot be seen from the repo: privacy policy URL, support URL, App Privacy answers, age rating questionnaire, export compliance, content rights declaration, contact info for App Review, pricing and availability, EU trader status under the Digital Services Act if distributing in the EU, and (optional) accessibility nutrition labels. Drop items already covered by a dedicated check.
