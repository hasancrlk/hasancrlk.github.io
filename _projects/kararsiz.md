---
title: "Put your finger on the screen: a multi-touch random picker called Kararsız"
kisa: Everyone puts a finger on the screen and the app picks one after a countdown. Multi-touch with Expo and React Native.
ozet: "I built a small mobile game for groups of friends who can't decide who washes the dishes. Small, but it taught me multi-touch handling and React's stale-state trap."
date: 2026-08-08
teknolojiler: [React Native, Expo, expo-router, expo-haptics, TypeScript]
repo: https://github.com/hasancrlk/Kararsiz
kategori: mobil-web
sira: 9
ref: kararsiz
---

## The idea

"Who pays?", "who goes first?" Everyone puts a finger on the phone screen, and
after a short countdown the app picks one. The chosen finger's ring grows and
the phone vibrates. *Kararsız* means "indecisive" in Turkish.

1. Tap **Start**.
2. Between 2 and 10 people put a finger on the screen.
3. As soon as the second finger lands, a 3-second countdown begins, with a
   vibration every second.
4. When it ends, one finger is picked at random.
5. When everyone lifts their fingers, the game resets.

## Tracking each finger separately

Every touch on the screen has an `identifier`. I keep the fingers in a `Map`
keyed by that identifier. If a finger moves, only its coordinates update; if
a new finger arrives, it gets a colour and joins the map:

```tsx
touches.forEach((t) => {
  const id = String(t.identifier);
  if (updated.has(id)) {
    updated.set(id, { ...updated.get(id)!, x: t.pageX, y: t.pageY });
  } else if (updated.size < MAX_FINGERS) {
    updated.set(id, { id, x: t.pageX, y: t.pageY,
                      colorIndex: updated.size % COLORS.length, isWinner: false });
  }
});
```

If someone lifts a finger during the countdown and at least two remain, the
countdown restarts. If fewer than two remain, it is cancelled. When the last
finger lifts, everything resets.

## The stale-state trap

This is what the project really taught me. The touch handlers are created
once with `useCallback`. If they read the `phase` state, they see the value
from when the function was created. In React this is called a "stale
closure". The result: even after the countdown had started, the handler still
thought it was idle and could start a second countdown.

The fix is to keep the state in a `useRef` as well. The `phase` state drives
rendering; the handlers read `phaseRef.current`, which is always current:

```tsx
const [phase, setPhase] = useState<'idle' | 'countdown' | 'selected'>('idle');
const phaseRef = useRef<'idle' | 'countdown' | 'selected'>('idle');
// ...
if (updated.size >= 2 && phaseRef.current === 'idle') {
  startCountdown(updated);
}
```

## Haptic feedback

With `expo-haptics` there is a medium vibration on every second of the
countdown, a "success" vibration at the moment of selection, and a strong
repeating vibration while the winning finger stays on the screen. Feeling the
result even with the phone lying on the table is what makes the game fun.

## What I learned

A small game turned out to be one of the best places to learn React's timing
model. When event handlers, timers and state change at the same time, "which
value am I actually seeing?" becomes the critical question. I also learned
that multi-touch behaves differently on web and mobile, and you can't be sure
without testing on a real device.
