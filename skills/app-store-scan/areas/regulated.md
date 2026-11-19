# regulated: gambling, VPN, device management, crypto, finance and other licensed fields

Guidelines 5.3, 5.4, 5.5, 3.1.5, 3.2.1, 3.2.2, 5.1.1(ix), 1.4.3, 1.7. Applies only when the app really operates in one of these fields. The signals are noisy (a "wallet" struct, "betting" in sample text): confirm from the app's purpose. If none apply, write one `REG-00` check with status `na` saying which signals were incidental, and stop. Report only the sections that apply; licensing itself is always `manual`. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**REG-01** `[all]` (5.3.3, 5.3.4 · blocker) Real-money gaming and lotteries: licensed in every place the app is used, geo-restricted to those places in code, free on the App Store, and never using in-app purchase to buy credit or currency for real-money play. No gambling aids such as card counters.

**REG-02** `[all]` (5.3.1, 5.3.2 · high) Sweepstakes, contests and raffles are sponsored by the developer, with official rules shown in the app stating Apple is not a sponsor or involved.

**REG-03** `[all]` (5.4 · blocker) VPN apps use `NEVPNManager`/NetworkExtension APIs, come from an organization account, state on screen before purchase or use what data is collected and how it is used, never sell or disclose user data to third parties (and say so in the privacy policy), and hold a VPN license where a territory requires one (provide it in review notes).

**REG-04** `[all]` (5.5 · blocker) MDM, configuration profiles and parental-control apps have Apple's capability approval, come from an eligible organization, declare data collection on screen before use, and do not sell or share data. Family Controls / Screen Time APIs need the distribution entitlement and may not be monetized as the built-in capability itself (4.10).

**REG-05** `[all]` (3.1.5 · blocker) Cryptocurrency: wallets only from organization accounts; no on-device mining; exchanges only where licensed; ICOs and crypto-securities only from established financial institutions; no crypto rewards for tasks such as downloading apps or posting to social networks.

**REG-06** `[all]` (3.2.1(viii), 3.2.2(viii),(ix) · blocker) Finance. Trading, investing and money-management apps are submitted by the licensed financial institution. No binary options. CFD and FOREX apps are licensed in every jurisdiction served. Personal loan apps disclose all terms including maximum APR and payment due date, cap APR at 36% including fees, and do not require full repayment within 60 days.

**REG-07** `[all]` (5.1.1(ix) · high, manual) Highly regulated fields (banking, financial services, healthcare, gambling, legal cannabis, air travel, crypto exchange) are submitted by the legal entity that provides the service, not an individual developer account.

**REG-08** `[all]` (1.4.3 · blocker) Controlled substances: no facilitating sale of tobacco, vaping products or controlled substances; licensed pharmacies and legal cannabis dispensaries are the exception and must be geo-restricted to the legal jurisdiction.

**REG-09** `[all]` (3.2.1(v),(vi), 3.2.2(iv) · high) Insurance apps are free and do not use in-app purchase. Fundraising inside the app only for Apple-approved nonprofits, with Apple Pay support and disclosure of how funds are used; otherwise donations are collected outside the app (Safari, SMS) and the app is free.

**REG-10** `[all]` (1.7, 1.4.4 · high) Crime-reporting apps involve local law enforcement and are offered only where that involvement is active. DUI checkpoints shown only when published by law enforcement.
