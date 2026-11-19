# kids: Kids Category and children's data

Guidelines 1.3, 5.1.4, 2.3.8, 2.5.13. Applies when the app is in or aimed at the Kids Category, is primarily for children, or collects personal data from minors. First decide which case this is from the app's content and wording; if the `kids` signal was incidental (a "kids" label in unrelated data), write one `KIDS-00` check with status `na` and stop. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**KIDS-01** `[all]` (1.3 · blocker) Kids Category apps keep links out of the app, purchasing opportunities and other distractions behind a parental gate (a task a young child cannot complete, not a simple tap or a birth-year field alone). Check every external link, share sheet, web view, review prompt, "more apps" and in-app purchase entry.

**KIDS-02** `[all]` (1.3, 5.1.4 · blocker) No third-party analytics or advertising in Kids Category apps or apps intended primarily for kids. Limited exception: analytics that collect no IDFA and no identifiable information about the child, location or device; contextual ads from a network with published kids-app policies and human review of creatives. Check every SDK in the dependency list against this.

**KIDS-03** `[all]` (1.3 · blocker) No personally identifiable information or device information sent to third parties. No IDFA use, no ATT prompt.

**KIDS-04** `[all]` (5.1.4 · blocker) A privacy policy exists and children's privacy laws (COPPA, GDPR-K and local equivalents) are followed. Collecting personal data from a child needs verifiable parental consent, which is a different thing from the parental gate. Report the legal part as `manual`.

**KIDS-05** `[all]` (2.3.8, 5.1.4 · high) Wording. "For Kids" / "For Children" and similar terms in name, subtitle, icon, screenshots or description are reserved for Kids Category apps; an app outside the category may not imply children are its main audience.

**KIDS-06** `[all]` (5.1.4 · high) Age questions are for compliance only. An app may ask birthdate or parental contact solely to comply with the law, and must still offer something useful regardless of age.

**KIDS-07** `[all]` (1.3 · high) Once in the Kids Category, always held to it: later updates must keep meeting these rules even after leaving the category. Mention if the project history suggests it was a kids app.

**KIDS-08** `[all]` (2.5.13, 2.5.18 · medium) Under-13 users get an alternative to face authentication; no behavioral ads based on kids' data anywhere.
