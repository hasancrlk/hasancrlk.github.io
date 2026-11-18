---
title: "Who goes down to get the food? The story of Kararsız"
kisa: Everyone puts a finger on the screen and the app picks one after a countdown. Born out of a need in a student dorm.
ozet: "In our state student dorm, when we ordered food someone had to go down to the security desk to collect it. We used this app to decide who."
date: 2026-08-08
teknolojiler: [React Native, Expo, expo-router, expo-haptics, TypeScript]
repo: https://github.com/hasancrlk/Kararsiz
kategori: mobil-web
sira: 9
ref: kararsiz
---

In our KYK (state student) dorm, food orders weren't delivered to the room;
someone had to go down to the security desk to collect them. I wrote this app
to decide who would go. Everyone puts a finger on the phone screen, and after
a short countdown the app picks one finger, and the person going down is
decided.

The name comes from that use. *Kararsız* means "indecisive" in Turkish: when
you have to choose but can't decide, you can split the options among fingers
and leave the result to the app.

## How it works

1. Tap **Start**.
2. Between 2 and 10 people put a finger on the screen.
3. As soon as the second finger touches the screen, a 3-second countdown
   begins, with a vibration every second.
4. When the countdown ends, one finger is picked at random. Its ring grows and
   the phone vibrates continuously.
5. When everyone lifts their fingers, the game resets.

## Tracking the fingers

Each touch on the screen has a unique `identifier`. Fingers are kept in a
`Map` keyed by it. A moving finger only has its position updated; a new
finger gets a colour:

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

If a finger lifts during the countdown and at least two remain, the countdown
restarts. If fewer than two remain, it is cancelled.

## Reading the current state

The touch handlers are created once with `useCallback`. If they read the
`phase` state directly, they see the value from when the handler was created.
In React this is known as a stale closure, and it can start a second
countdown while one is already running.

So the game phase is also kept in a `useRef`. The `phase` state drives
rendering; the handlers read `phaseRef.current`, which is always current:

```tsx
const [phase, setPhase] = useState<'idle' | 'countdown' | 'selected'>('idle');
const phaseRef = useRef<'idle' | 'countdown' | 'selected'>('idle');

if (updated.size >= 2 && phaseRef.current === 'idle') {
  startCountdown(updated);
}
```

## Haptics

With `expo-haptics` there is a medium vibration on every second of the
countdown, a success vibration at the moment of selection, and a strong
repeating vibration while the winning finger stays on the screen. Feeling the
result while the phone lies in the middle of the table is the most important
part of the game.

When we first tried the app on a real phone, I liked the result.
