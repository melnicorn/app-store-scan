# tv-watch-vision: tvOS, watchOS and visionOS specifics

Small platform add-ons to the shared areas. Report only the checks for platforms the project targets. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**TV-01** `[tvos]` (2.4.3 · blocker) Fully usable with the Siri Remote alone; other peripherals may add to the experience. If a game controller is required, the listing must say so and the target must declare it (`GCSupportsControllerUserInteraction`, required controller capability).

**TV-02** `[tvos]` (2.1, upload · high) tvOS assets and behavior: layered app icon and Top Shelf image present; focus engine navigation works on every screen (no elements unreachable by focus); Menu button backs out and exits from the root; no reliance on persistent local storage beyond the small guaranteed allowance (use iCloud or on-demand resources).

**TV-03** `[tvos]` (5.1.1(v) · medium) Account deletion on tvOS may be a static URL or QR code to the deletion page; sign-in should offer a companion-device or code flow rather than long text entry.

**WATCH-01** `[watchos]` (2.5.18 · blocker) No display advertising in the watch app.

**WATCH-02** `[watchos]` (4.2, 2.5.16 · high) The watch app does something useful on the watch itself and relates to the iOS app's function; complications and notifications show the app's own content. A watch-only or independent app (`WKRunsIndependentlyOfCompanionApp`) must work without the phone.

**WATCH-03** `[watchos]` (upload · high) Watch plumbing: bundle ids nested under the companion app's id (`WKCompanionAppBundleIdentifier`), versions match, watch icon set complete, 64-bit arm64 build, health and motion purpose strings present in the watch target itself.

**VISION-01** `[visionos]` (2.3, visionOS submission guidance · medium) Described as a spatial computing app. Listing and in-app text should not call the experience AR, VR, XR or MR; refer to the device as Apple Vision Pro (never abbreviated or generically "headset").

**VISION-02** `[visionos]` (5.1, 2.5.14 · high) Sensitive spatial data: hand tracking, world sensing and camera access each need purpose strings (`NSHandsTrackingUsageDescription`, `NSWorldSensingUsageDescription`), are requested only inside the immersive experience that needs them, and are never used for advertising or profiling (5.1.2(vi)).

**VISION-03** `[visionos]` (1.4, HIG · medium) Comfort and safety: immersive experiences do not encourage movement that risks injury, give a clear way to exit, and avoid motion patterns known to cause discomfort. Motion-heavy content should be declared in App Store Connect.

**VISION-04** `[visionos]` (2.4.1 · low) Compatible iPad/iPhone apps are offered on Apple Vision Pro automatically unless opted out: if the app depends on hardware visionOS lacks (GPS, some sensors, back camera use cases), opt out or handle absence gracefully.
