---
title: "Focus without touching your phone and earn points: Pomodoro Plus"
kisa: A mobile-first (PWA) pomodoro app that rewards putting your phone down with points.
ozet: "I built a pomodoro app for people who can't put their phone down. Finishing a focus session without touching the phone earns more points, and points unlock new themes."
date: 2026-08-11
teknolojiler: [Next.js, TypeScript, Tailwind CSS, Zustand, PWA]
repo: https://github.com/hasancrlk/Pomodoro_Plus
kategori: mobil-web
sira: 8
ref: pomodoro
---

## The idea

The Pomodoro technique is simple: focus for 25 minutes, take a 5-minute
break. The trouble is that the biggest distraction is usually the device the
timer runs on. For someone who starts the timer and opens social media three
minutes later, a classic timer changes nothing.

Pomodoro Plus **rewards** leaving the phone alone:

| Event | Effort points |
|---|---:|
| Focus session finished without touching the phone | +12 |
| Focus session finished, but the phone was touched | +6 |
| Break finished | +2 |
| Timer cancelled | −5 |

Points unlock new themes in the shop (Gold, Neon, Forest, Ocean), an extra
break and badges.

## How does it know you touched the phone?

A web app can't see overall phone usage. The best approximation available is
watching whether the page goes to the background. When the user switches to
another app, the browser fires `visibilitychange`:

```tsx
useEffect(() => {
  function onVisibilityChange() {
    if (document.hidden) markDistracted();
  }
  document.addEventListener("visibilitychange", onVisibilityChange);
  return () => document.removeEventListener("visibilitychange", onVisibilityChange);
}, [markDistracted]);
```

This measurement is **approximate**: turning off the screen and leaving the
phone on the desk also hides the page. I say this openly in the README. Real
"screen time" measurement needs native APIs, which would mean moving the app
to something like React Native.

## Emergency contacts

During a focus session the other tabs are locked. The one exception is the
user's **emergency contacts**, who can be called through a `tel:` link.
Focusing matters, but not so much that you can't call your mother.

## Under the hood

- **State:** Zustand. Points, point history, emergency contacts, purchases
  and the active theme are persisted in the browser. No server, no account.
- **PWA:** a `manifest.webmanifest` and a small service worker make it
  installable to the home screen, with basic offline caching.
- **UI:** Next.js App Router, Tailwind CSS v4, a circular countdown
  animation.

## What I'd do differently next time

The timer currently decrements the remaining time by one every second.
Browsers throttle timers in background tabs, so it can drift. The more
accurate approach is to store the end time and compute the remaining time from
it on every tick. Notifications at the end of a session and a statistics
screen are also missing. The point history is already stored; it just needs a
view.

## What I learned

I learned to recognise the limits of the web platform. Making a feature
"approximate" is fine as long as you tell the user honestly. In gamification I
also saw that penalties should stay smaller than rewards. With a big
cancellation penalty, people would avoid opening the app at all.
