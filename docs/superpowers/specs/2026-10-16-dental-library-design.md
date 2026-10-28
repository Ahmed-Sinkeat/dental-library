# Bilingual dental teaching library

## Agreed outcome

A public, mobile-friendly website for the doctor's dental lessons. Visitors
browse, search, read, listen, watch, and download without creating accounts.
The interface supports Arabic and English. The doctor has protected content
management. Telegram migration is postponed because the user's data is limited.

## First implementation milestone

Build the public library locally with clearly labeled sample lesson metadata.
Include home, subject, lesson, references, and exam pages. Do not download
Telegram attachments, provision paid services, or deploy publicly in this milestone.
Subsequent milestones connect Cloudflare storage and add protected management.

## Presentation and language

- Use a restrained academic layout: light background, dark text, teal accents,
  readable typography, subject cards, and a simple header with search and language switching.
- Use Arabic as the default at `/`, redirecting to `/ar/`; English lives at `/en/`.
- Switching language preserves the current subject or lesson where possible.
- Set document language and direction correctly: Arabic RTL, English LTR.
- Translate interface labels and sample descriptions; retain original clinical
  terminology and original filenames. Existing teaching materials are not translated.
- Use system fonts and no remote font downloads or decorative stock images.
- Provide semantic navigation, labeled controls, keyboard focus, adequate contrast,
  and layouts usable on narrow screens.

Arabic default and the visual treatment are proposed defaults, not requirements
previously specified by the user.

## Public pages

- Home: purpose, subject navigation, search, and a clear sample-content notice.
- Subject: its description and ordered lesson list.
- Lesson: title, description, ordered attachments, source link, and availability.
- References and exams: separate catalog sections using the same lesson structure.
- Search: match Arabic and English titles, descriptions, and subjects. Search
  does not inspect attachment contents or transcribe recordings.
- Missing records have a useful 404; no-result searches offer a clear reset.

Use a small local data file for the initial catalog. It is sample metadata, not
an assertion that Telegram files have been imported. A lesson with no uploaded
attachments shows an explicit unavailable state and its Telegram source link;
it must not show fake playback or download buttons.

## Reading, playback, and downloads

Use native audio/video controls for compatible files. Display file type and size
when known. Reading copies of presentations and Word documents will be PDFs;
originals remain downloadable. Provide open/download alternatives where inline
PDF viewing is unavailable. Do not preload large media or load video embeds
before the visitor requests them. Browser media compatibility is verified when
real files are introduced, with conversion only where required.

## Cloudflare architecture

- Astro with TypeScript on Workers serves pages and later admin endpoints.
- D1 stores subjects, lessons, attachments, ordering, publication state, and source references.
- R2 stores original files and later reading/playback copies. Files do not belong in Git.
- Cloudflare Access protects admin pages and all mutation endpoints. Validate
  Access tokens server-side and prevent alternate deployment URLs bypassing protection.
- Keep unpublished materials private. Public delivery includes only approved files.
- Store secrets outside source control. Do not reuse or extract browser Telegram credentials.

The minimal data model is subjects, lessons, and attachments. Lessons belong to
a subject and have a category of teaching, reference, or exam. An attachment
belongs to a lesson and has an ordered position, file type, storage key or approved
external URL, and optional size. Keep one stable slug across languages and separate
Arabic/English titles and descriptions. Do not add student tables.

## Doctor management milestone

Add subject and lesson editing, attachment upload/order, and draft/publish controls.
Validate input and file metadata, restrict external URL schemes, and escape text.
Large uploads go directly to R2 using authenticated upload authorization, with
multipart uploads where necessary. Incomplete uploads must not publish lessons.
Do not add a separate CMS or custom password system.

## Deferred migration

Prefer a channel-only Telegram Desktop JSON export with attachments when data is
available. Preserve an untouched archive. Inventory missing files, counts, sizes,
and checksums; keep message IDs and captions. Import into private storage and draft
records, with safe reruns and a failure report. Do not deduplicate solely by filename
or automatically infer ambiguous lesson groupings without review.

## Verification

For the first milestone, run Astro build and type checks. Add one small runnable
self-check for catalog integrity, bilingual search, and language-route mapping,
including no matches, invalid references, and unavailable attachments.
No screenshot tests or heavy end-to-end suite. The user reviews appearance.
Cloudflare integration later requires a local dry-run and authorization checks;
migration later requires comparing inventories and verifying transferred bytes.

## Out of scope

Student accounts, payments, quizzes, comments, offline caching, automatic Telegram
sync, AI features, transcripts, and bulk media transfers during the first milestone.

## Risks and launch conditions

An exported or public Telegram file is not automatically licensed for redistribution.
The doctor reviews third-party material and patient information before publication.
Storage costs remain unknown until the inventory exists. Configure backups and
document recovery before treating Cloudflare as the sole copy of teaching materials.
Do not present a sample site as a completed migration or an unsecured admin as ready.
