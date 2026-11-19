# health: health, fitness and medical

Guidelines 1.4.1, 1.4.2, 5.1.3, 5.1.2(vi), 2.5.1. Applies when the app uses HealthKit, CareKit, ResearchKit, Motion & Fitness for health purposes, or makes health or medical claims. If `medical_claims` matched unrelated wording, write one `HLTH-00` check with status `na` and stop. Each check: **ID** `[platform]` (guideline · usual severity when it fails).

**HLTH-01** `[all]` (1.4.1 · blocker) No unverifiable measurement claims. Apps may not claim to measure blood pressure, body temperature, blood glucose, blood oxygen, or take x-rays using only the device's sensors. Any accuracy claim about a health measurement must come with disclosed data and methodology. Check marketing strings and feature names.

**HLTH-02** `[all]` (1.4.1 · high) Medical information carries a reminder to consult a doctor before making medical decisions, shown in the app near the relevant output. Apps used for diagnosis or treatment get extra scrutiny: regulatory clearance (FDA or equivalent), if any, should be linked in the submission (`manual`).

**HLTH-03** `[all]` (1.4.2 · blocker) Drug dosage calculators come only from a manufacturer, hospital, university, insurer, pharmacy or other approved entity, or have regulatory approval.

**HLTH-04** `[all]` (5.1.3(i), 5.1.2(vi) · blocker) Health data is never used for advertising, marketing or data mining, and is not disclosed to third parties except for health management or research with permission. Trace HealthKit, motion and health-form data: it must not reach analytics, ad or attribution SDKs. The app discloses which specific health data it collects.

**HLTH-05** `[all]` (5.1.3(ii) · blocker) No false or inaccurate data written to HealthKit, and no personal health information stored in iCloud (check CloudKit, iCloud Documents, `NSUbiquitousKeyValueStore` and backup inclusion of health files).

**HLTH-06** `[all]` (5.1.3(iii),(iv) · high) Human-subject research has informed consent covering purpose, procedures, risks, confidentiality and data sharing, a contact, and how to withdraw; minors need guardian consent; an independent ethics board has approved it (`manual` for the approval itself).

**HLTH-07** `[all]` (2.5.1, 5.1.1 · high) HealthKit is used for health and fitness and integrated properly: capability enabled in entitlements, `NSHealthShareUsageDescription` / `NSHealthUpdateUsageDescription` specific to the data types, only the types actually needed are requested, and the description mentions Health integration.

**HLTH-08** `[all]` (5.1.3(i) · medium) Benefits tied to health data (for example insurance discounts) are offered only by the entity providing the benefit, and the data is not shared onward.
