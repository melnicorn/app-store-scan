# completeness: app completeness and build requirements

Guidelines 2.1, 2.2, 2.3.1 and App Store Connect upload validation. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**COMP-01** `[all]` (upload · blocker) Built with an accepted Xcode and SDK. Compare the `xcode` fact and hint with `requirements.json` (`current`, `upcoming`). Fail if below the current minimum; warn if the upcoming minimum takes effect within about three months and the toolchain is older. CI configs (`.github/workflows`, `fastlane/Fastfile`, `.xcode-version`, `ci_scripts`) may pin an older Xcode than the local one: check them.

**COMP-02** `[all]` (upload · blocker) Deployment target at or above the minimum. Use the `build` fact. Warn when it falls below the upcoming minimum.

**COMP-03** `[all]` (2.1(a) · high) No placeholder or temporary content in shipped UI: lorem ipsum, "coming soon", TODO screens, empty tabs, sample data presented as real, stub buttons with no action, example.com links. Follow the `placeholder` signal, then skim the main navigation (tab bar, sidebar, settings) for dead ends. A feature that is visibly unfinished is a rejection even if nothing crashes.

**COMP-04** `[all]` (2.2 · high) Not a beta, demo or trial. Fail when user-facing strings, the display name or the version label call the app beta/demo/preview/test, or when a "full version coming later" message exists. Version numbers like 0.1.0 are allowed but read as unfinished: warn (low) and suggest 1.0.

**COMP-05** `[all]` (2.1(a) · high) Release builds talk to live services. Check the `dev_endpoints` signal and base-URL configuration: fail when a release build would use localhost, a LAN address, staging or a tunnel as a hardcoded server. A LAN address chosen by the user at runtime, or discovered on the local network, is fine. Manual: backend must be up during review.

**COMP-06** `[all]` (upload · blocker) App icon present and complete. An `AppIcon` asset (or Icon Composer `.icon` file) must exist with a 1024 px image; on iOS-family platforms it must be opaque (ITMS-90717). Fail on the hint after confirming there is no icon elsewhere (search for `*.appiconset`, `*.icon`, `CFBundleIcons`). Also confirm `ASSETCATALOG_COMPILER_APPICON_NAME` names an asset that exists.

**COMP-07** `[ios]` (upload · blocker) Launch screen configured (`UILaunchScreen` or `UILaunchStoryboardName`). If the app supports iPad multitasking it also needs all four iPad orientations or `UIRequiresFullScreen`.

**COMP-08** `[all]` (upload · low) Export compliance answered. Check the `custom_crypto` signal first. If the app contains its own or third-party cryptography (OpenSSL, libsodium, a hand-written cipher, in any language compiled into the app), this is `manual`: the developer must work out whether an exemption applies and may need documentation, and that takes precedence over the missing key. Otherwise, if `ITSAppUsesNonExemptEncryption` is absent, warn (low) and recommend setting it to `false` (HTTPS and OS-provided encryption are exempt).

**COMP-09** `[all]` (2.1(a) · high, manual) Reviewer can reach everything. If the app needs an account, hardware, a companion device, a specific network, a QR code or paid content to show its features, App Review needs a demo account, a demo mode, or a video and explanation in the review notes. Decide from the code what a reviewer with a bare device would see on first launch; if the answer is "an empty or blocked screen", report `manual` with exactly what to supply (and consider recommending a built-in demo mode). This is one of the most common rejection causes for hardware- or network-dependent apps.

**COMP-10** `[all]` (2.1(a) · high) No obvious crash on first run. Check the `crash_risk` signal on the launch path and main flows: `fatalError`, `try!`, force casts and force unwraps of network, file or user data; `unwrap`/`expect`/`panic!` in Rust or other native code reachable through FFI (a panic there aborts the app); unhandled denied permissions; missing bundled resources (fonts, models, files referenced by name that are not in the project). Only report ones a reviewer could plausibly hit.

**COMP-11** `[all]` (2.1(a) · medium) Links work. Collect outward URLs in the app (support, privacy, terms, website, social). Flag ones that are obviously placeholders or malformed; list the rest as a single `manual` check to confirm they load.

**COMP-12** `[all]` (upload · blocker) Identity is real: bundle identifier is not a template default, `CFBundleShortVersionString` and `CFBundleVersion` are set and agree with the build settings (a literal in Info.plist overrides `MARKETING_VERSION`; mismatches are a `warn`, low), display name is final and matches the intended App Store name closely enough to avoid confusion (2.3.8).

**COMP-13** `[all]` (2.3.1(a) · medium) Debug-only UI is compiled out. Follow `debug_only`: developer menus, log viewers, environment switchers and test purchase buttons must sit behind `#if DEBUG` (or equivalent) rather than a runtime flag.
