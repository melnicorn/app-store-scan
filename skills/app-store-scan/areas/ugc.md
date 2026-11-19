# ugc: user-generated content, AI-generated content, mini apps and chatbots

Guidelines 1.2, 1.2.1, 4.7, 5.1.2(i). Applies when users can post, upload, share, chat or generate content that other people can see, when the app generates content with AI, or when it hosts software not in the binary. Content that never leaves the user's own device or account (private notes, a personal library) is not UGC for 1.2. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**UGC-01** `[all]` (1.2 · blocker) Objectionable content is filtered before or as it is posted: automated filtering, moderation queue, or both. Look for a moderation call on the upload/post path or evidence of server-side moderation; if only server-side, `manual` asking the developer to describe it in review notes.

**UGC-02** `[all]` (1.2 · blocker) Users can report content, and reports are acted on promptly. A report or flag action must be reachable from every piece of user content (posts, comments, profiles, messages, AI outputs shared publicly).

**UGC-03** `[all]` (1.2 · blocker) Users can block abusive users, and blocking hides that user's content immediately.

**UGC-04** `[all]` (1.2 · high) Published contact information so users can reach the developer, in the app.

**UGC-05** `[all]` (1.2 · high) Terms that prohibit objectionable content and abusive behavior, accepted before posting (a EULA or community rules shown at sign-up). Reviewers routinely ask for this with the three items above.

**UGC-06** `[all]` (1.2 · blocker) Not the wrong kind of service: primarily pornographic content, Chatroulette-style random video chat, anonymous or random chat with strangers, "hot or not" rating of real people, anonymous bullying. NSFW content from a web service must be hidden by default and only enabled from the developer's website.

**UGC-07** `[all]` (1.2, 5.1.2(i), 2.3.6 · high) AI-generated content is treated as user-generated content. If the app generates text, images, audio or video from prompts: prompts and outputs are filtered for objectionable and nonconsensual intimate content; users can report outputs; the age rating reflects what can be generated; and sending user content to a third-party AI provider is disclosed with explicit permission (see `privacy` PRIV-03). Chatbots that can produce mature content need age restriction.

**UGC-08** `[all]` (1.2.1 · high) Creator-content apps let users identify content that exceeds the app's age rating and restrict it by verified or declared age (for example the Declared Age Range API); paid creator content is clearly marked and sold through in-app purchase.

**UGC-09** `[all]` (4.7 · high) Mini apps, mini games, streaming games, chatbots, plug-ins and emulators offered inside the app: each follows the privacy rules, has filtering/report/block, uses in-app purchase for digital goods; native APIs are not exposed to them without Apple's permission (4.7.2); data and permissions are not shared with them without per-instance consent (4.7.3); the app provides an index with universal links to each (4.7.4); content exceeding the age rating is identifiable and age-restricted (4.7.5). Emulators may download games, and the developer is responsible for their legality.

**UGC-10** `[all]` (5.1.1(v) · medium) Deleting an account also removes that user's shared content (cross-check with `accounts` ACCT-02).
