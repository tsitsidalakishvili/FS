# Deliberation Participate Mobile (Expo / React Native)

Cross-platform anonymous participation app for Android + iOS.

## Features in this MVP

- Conversation picker (from `/participation/conversations`)
- Tinder-style swipe voting deck:
  - swipe right = agree (`choice=1`)
  - swipe left = disagree (`choice=-1`)
  - swipe up or tap = pass (`choice=0`)
- Anonymous participant identity persisted on device
- Offline vote queue using SQLite + automatic retry sync
- Optional invite token support (`X-Invite-Token`)
- Optional comment submission per conversation setting

## Configure API URL

Set the API base URL before running:

```bash
cd deliberation/mobile
export EXPO_PUBLIC_DELIBERATION_API_URL="http://<your-api-host>:8010"
```

If not set, the app falls back to `app.json` extra value, then `http://localhost:8010`.

## Run

```bash
cd deliberation/mobile
npm install
npm run start
```

Then:
- press `a` for Android emulator/device
- press `i` for iOS simulator (macOS only)
- or scan QR in Expo Go

## Notes

- The app does **not** collect PII.
- Backend should already support:
  - `POST /vote` with `X-Participant-Id`
  - `GET /participation/conversations`
  - `GET /participation/conversations/{id}/deck`

