# macos: Mac App Store requirements

Guideline 2.4.5 plus Mac upload validation. Load only when macOS is a target (native AppKit/SwiftUI, Mac Catalyst, Electron `mas` builds, Tauri, Flutter macOS). These rules are for Mac App Store distribution; a Developer ID build of the same app outside the store is not bound by them, so check which build configuration ships to the store. Every check here is `[mac]`. Each check: **ID** (guideline · usual severity when it fails).

**MAC-01** (2.4.5(i) · blocker) App Sandbox is on. `com.apple.security.app-sandbox` = true in the entitlements of the app and of every helper, XPC service, login item and embedded executable (helpers also need `com.apple.security.inherit` or their own sandbox). Missing sandbox fails upload.

**MAC-02** (2.4.5(i) · high) Entitlements are minimal and justified. For each `com.apple.security.*` entitlement find the feature that needs it. `temporary-exception` entitlements (absolute file paths, mach lookups, Apple Events to arbitrary apps, home-relative paths) require written justification and are frequently refused. Prefer `files.user-selected.read-only` over read-write; network client/server only if used; `device.*` and `personal-information.*` only with matching purpose strings. `com.apple.security.cs.disable-library-validation`, `allow-jit`, `allow-unsigned-executable-memory` need a real reason (Electron needs `allow-jit`).

**MAC-03** (2.4.5(vii) · blocker) Updates only through the Mac App Store. No Sparkle, Squirrel, electron-updater, Tauri updater, custom "check for updates", or `SUFeedURL` in the store build. Code may remain if compiled out or disabled for the store configuration: verify it.

**MAC-04** (2.4.5(vi), 3.1.1 · blocker) No license screen at launch, license keys, serial numbers, activation servers or custom copy protection. Paid features use in-app purchase; receipt validation is the only allowed protection. Third-party licensing SDKs (Paddle, FastSpring, DevMate, Gumroad) must be absent from the store build.

**MAC-05** (2.4.5(iii) · high) No auto-launch or lingering processes without consent. Launch-at-login must be an opt-in setting using `SMAppService` (or the older `SMLoginItemSetEnabled` helper); no LaunchAgents/LaunchDaemons written to disk; no processes left running after the user quits unless the user asked for it (menu-bar helper they enabled). No adding the app to the Dock or dropping shortcuts on the Desktop.

**MAC-06** (2.4.5(v) · blocker) No root. No `AuthorizationExecuteWithPrivileges`, `SMJobBless` privileged helpers, `sudo`, setuid binaries, or AppleScript "with administrator privileges".

**MAC-07** (2.4.5(iv), 2.5.2 · blocker) Does not download or install more software: no standalone apps, kexts, system extensions installed outside the bundle, installers (`.pkg`, `.dmg`), package-manager installs (`brew`, `pip`, `npm`), or scripts fetched and run. System and DriverKit extensions are allowed only embedded in the bundle with the proper entitlements.

**MAC-08** (2.4.5(i), 2.5.2 · high) File access stays within the sandbox model: the app container, app groups, and files the user picked (`NSOpenPanel`/`NSSavePanel`, drag and drop) kept via security-scoped bookmarks with balanced `startAccessing`/`stopAccessing`. Hardcoded paths under `~/`, `/Users`, `/Library`, `/usr/local`, `/Applications` will fail at runtime. Other apps' data (contacts, calendars, bookmarks) only through the system APIs. Spawning shell commands (`Process`, `NSTask`, `child_process`, `Command::new`) works only for sandbox-compatible binaries inside the bundle: check each use.

**MAC-09** (2.4.5(ii) · high) Self-contained single bundle, packaged with Xcode tooling: no third-party installers, nothing installed into shared locations, all helpers and resources inside the `.app`. Signed with a Mac App Distribution identity and packaged as a `.pkg` by Xcode or `productbuild`.

**MAC-10** (2.4.5(viii) · high) Runs on the current macOS without optional or deprecated technology: no Java runtime dependency, no Rosetta requirement (ship arm64 or universal; x86_64-only builds are a problem), no system Python/Ruby/Perl dependency, no legacy `WebView`, QTKit, Carbon or OpenGL-only paths where they break. Check `ARCHS` and bundled binaries' architectures.

**MAC-11** (upload · blocker) Upload hygiene: hardened runtime enabled; no `com.apple.quarantine` extended attribute on any bundled file (strip with `xattr -cr` before archiving); `LSApplicationCategoryType` set; `LSMinimumSystemVersion` set; app icon in `.icns` or asset catalog with all sizes; all embedded frameworks and helpers signed with the same team.

**MAC-12** (2.4.5(ix) · low) All localizations ship inside the one bundle; no language packs downloaded later.

**MAC-13** (2.5.1, 2.5.14 · high) System access prompts are justified: Accessibility (`AXIsProcessTrusted`), input monitoring/event taps, screen recording, Apple Events automation (`NSAppleEventsUsageDescription` plus `com.apple.security.automation.apple-events`), Full Disk Access. Many of these do not work in the sandbox at all (Accessibility control of other apps, global event taps beyond listen-only, Full Disk Access prompts): if a core feature depends on one, the app may not be viable on the Mac App Store. Say so plainly.

**MAC-14** (2.5.1 · high) Framework-specific traps. Electron: build the `mas` target, not `darwin`; use the MAS build of Electron (the regular one references private APIs and is rejected); `ElectronTeamID`, provisioning profile embedded; helpers signed with inherit entitlements; no `autoUpdater`, no `crashReporter` upload without consent. Tauri: updater plugin disabled, sandbox entitlements added, bundled as `.app` then `.pkg`. Catalyst: the Mac build is reviewed as a Mac app, including these rules and Mac-appropriate UI (menus, window resizing, keyboard).

**MAC-15** (4, HIG · low) Behaves like a Mac app: quits or stays alive sensibly when the last window closes, has a working menu bar with standard items, supports window resizing where content allows, and does not show iOS-only wording ("tap", "home screen").
