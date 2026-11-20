# How Inkpad stores your work

Internal support reference. Last reviewed 2 November 2026.

## Where drafts live

Every draft is stored on the Inkpad server, in the user's account. When the user is online, the desktop app saves the
open draft to the server every 10 seconds and whenever they switch drafts. Signing in on another device shows the same
drafts.

## What the cache holds

The cache is a local folder on the user's device. It holds:

- offline copies of recently opened drafts, so they open without a connection;
- the search index for the user's drafts;
- thumbnails and images inserted into drafts.

The cache grows with use and is not trimmed automatically before version 6.0. Above about 4 GB, opening drafts and
searching slow down noticeably, especially on laptops with 8 GB of memory or less.

## Clearing the cache

Settings > Storage > Clear cache deletes the local folder. It does not delete drafts: they stay on the server. After
clearing, the app re-downloads each draft the next time the user opens it, and rebuilds the search index in the
background, which takes a few minutes for a typical account. Search results can be incomplete until it finishes.

One exception: changes made while offline are kept only in the cache until they sync. Before clearing, the user should
check that the sync icon at the bottom left shows a cloud with a tick, meaning every change has reached the server. If it
shows a cloud with an arrow, they should stay online until it changes.

## Exporting drafts

File > Export all drafts saves every draft as a Markdown file in a folder the user chooses. Export is not needed before
clearing the cache, but users who want a local copy can use it at any time.
