# accounts: sign-in, account creation and deletion

Guidelines 4.8, 5.1.1(v), 2.1(a), 2.5.13. Applies when the app has any sign-in. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**ACCT-01** `[all]` (4.8 · blocker) An equivalent privacy-preserving login is offered next to third-party logins. If the app uses Google, Facebook, X, LinkedIn, Amazon, WeChat or similar to create or sign in to the user's primary account, it must also offer a login service that limits collection to name and email, lets users hide their email, and does not track for ads without consent. Sign in with Apple is the standard way to satisfy this. Exempt: only the company's own account system; education/enterprise apps using existing org accounts; government or industry eID; clients for a specific third-party service where signing in to that service is the point. Confirm the option appears on every sign-in and sign-up screen with equal prominence, on every platform the app ships on.

**ACCT-02** `[all]` (5.1.1(v) · blocker) Account deletion can be started inside the app. If accounts can be created (including automatically created guest accounts, and sign-up that happens on the web), the app needs an easy-to-find option that deletes the account and its data, not just deactivation or sign-out. A link straight to a web deletion page is acceptable; "email support" or a phone call is not, except in highly regulated industries. Find the entry point in settings or profile and trace it to a real delete call. Follow `account_deletion`.

**ACCT-03** `[all]` (5.1.1(v) · high) No forced login for features that do not need an account. If the app has features that work without server-side identity, they must be usable before signing in. Check what the first screen is and whether a login wall precedes everything. Core functionality must not depend on a specific social network login.

**ACCT-04** `[all]` (2.1(a) · high, manual) App Review can sign in. A working demo account (or approved demo mode) with full access goes in App Store Connect; two-factor, invite codes, SMS verification and region locks must not block the reviewer. Report as `manual`, noting any of those obstacles you see in the code.

**ACCT-05** `[all]` (5.1.1(v) · high) Sign in with Apple accounts are revoked on deletion. If Sign in with Apple is used, deleting the account must call the token revocation endpoint (`/auth/revoke`, or the SDK's equivalent such as Firebase `revokeToken`), and the app should handle credential-revoked notifications. Look for it in the delete flow or note that it must exist server-side (`manual` if not visible).

**ACCT-06** `[all]` (5.1.1(v) · medium) Social credentials are handled properly: tokens for social networks are stored only on device (Keychain), used only to talk to that network, and the app offers a way to disconnect the social account from within the app.

**ACCT-07** `[all]` (4, 5.1.1(v) · medium) Sign-up happens in the app. Sending users to the default browser to register or sign in is treated as poor UX and gets rejected; use in-app flows or `ASWebAuthenticationSession`. The Sign in with Apple button follows the HIG (system button or correct styling, not a custom lookalike with altered logo).

**ACCT-08** `[all]` (2.5.13 · medium) Biometric sign-in uses `LocalAuthentication` (not ARKit or custom face matching) and offers another method for users under 13. Needs `NSFaceIDUsageDescription`.

**ACCT-09** `[all]` (5.1.1(v), 5.1.1(x) · medium) Sign-up asks only for what is needed. Flag mandatory fields unrelated to the app's function (phone, birthdate, gender, address). Age collection is acceptable for legal compliance.
