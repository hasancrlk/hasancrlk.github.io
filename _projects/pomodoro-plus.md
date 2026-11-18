---
title: "A focus app I'm building for myself: Pomodoro Plus"
kisa: A mobile-first (PWA) pomodoro app that rewards putting your phone down with points. Work in progress.
ozet: "I'm building Pomodoro Plus for my own study routine. Finishing a focus session without touching the phone earns more points. The app is still in development; the goal is the App Store and Google Play."
date: 2026-08-11
teknolojiler: [Next.js, TypeScript, Tailwind CSS, Zustand, PWA]
repo: https://github.com/hasancrlk/Pomodoro_Plus
kategori: mobil-web
sira: 8
ref: pomodoro
---

> **Status:** The app is in development. Once it is complete I plan to
> publish it on the App Store and Google Play. This post describes the
> current version.

The Pomodoro technique is 25 minutes of focus followed by a 5-minute break. I
started writing this app for my own study routine. A classic timer shows how
much time is left but has no interest in whether the phone is in your hand
while it runs. The core idea of Pomodoro Plus is to encourage putting the
phone down with a points system.

## Points

- Focus session finished without touching the phone: **+12** points.
- Focus session finished, but the phone was touched: **+6** points.
- Break finished: **+2** points.
- Timer cancelled: **−5** points.

The cancellation penalty is kept smaller than the rewards; the aim is to
encourage finishing a session, not to discourage opening the app. Points
unlock the Gold, Neon, Forest and Ocean themes, an extra break and badges in
the shop.

## Detecting that the phone was touched

A web app can't access overall device usage. The closest available signal is
whether the app page goes to the background. When the user switches to
another app, the browser fires a `visibilitychange` event:

```tsx
useEffect(() => {
  function onVisibilityChange() {
    if (document.hidden) markDistracted();
  }
  document.addEventListener("visibilitychange", onVisibilityChange);
  return () => document.removeEventListener("visibilitychange", onVisibilityChange);
}, [markDistracted]);
```

This is an approximation. Turning off the screen also hides the page and
fires the same event. Accurate screen-time measurement requires native device
APIs; that is on the roadmap for the store version.

## Emergency contacts

During a focus session the rest of the app is locked. The one exception is
the emergency contacts the user added beforehand, who can be called through a
`tel:` link.

## Technical structure

- **UI:** Next.js App Router, TypeScript and Tailwind CSS v4. The timer is
  shown with a circular countdown animation.
- **State:** Zustand. Points, point history, emergency contacts, purchases
  and the active theme are persisted in the browser. No server or account
  needed.
- **PWA:** a web manifest and a service worker make the app installable to
  the home screen, with basic offline caching.

## Next steps

- The timer currently decrements the remaining time by one every second.
  Browsers throttle timers in background tabs, so the time can drift. Storing
  the end time and computing the remaining time from it is more accurate.
- A notification when a session ends.
- A statistics screen; the point history is already stored.
- Native screen-time integration for the store version.
