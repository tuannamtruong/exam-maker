# Flashcards — Android web app (PWA)

A simplified, read-only port of the flashcards desktop app. Flip / next / prev,
shuffle, search, jump-to-#, and a local "backlog" (hide list). **No add or edit**
— it reads `cards.json`, which is generated from the source `.md` files.

## Run it on your phone (WSL setup — serve from Windows)

WSL2 is NAT'd, so a server started *inside* WSL is not reachable from the phone.
Instead, serve this folder from **Windows**, which reads the WSL files directly
over `\\wsl.localhost\...` and binds to the real LAN.

1. In Explorer go to
   `\\wsl.localhost\Ubuntu\home\nam\exam-maker\webapp` and double-click
   **`serve-windows.cmd`** (or run it from a Windows terminal). Equivalent one-liner:

   ```
   py -3 -m http.server 8000 --directory \\wsl.localhost\Ubuntu\home\nam\exam-maker\webapp
   ```

2. First run: Windows Defender Firewall asks to allow Python → click **Allow**
   (tick *Private networks*).
3. On the phone (same Wi-Fi) open **`http://192.168.178.21:8000`**, then
   **browser menu → Add to Home Screen**. It launches full-screen and works
   offline (a service worker caches the app + cards on first load).

> The Wi-Fi IP `192.168.178.21` is this PC's current address — if it changes,
> find the new one with `ipconfig` on Windows (the Wi-Fi adapter's IPv4).

## Updating the cards

When you add cards, rebuild the data in WSL:

```bash
python3 scripts/gen_webapp.py     # rewrites webapp/cards.json
```

The Windows server serves the same folder live, so just reload the app on the
phone while online; offline it shows the last cached set. (`./run.sh webapp`
also rebuilds the data, but its built-in WSL server won't reach the phone — use
the Windows launcher above for that.)

## Backlog (hide list)

Source `.md` files are read-only here, so "backlog" is stored on the device
(`localStorage`), not by moving files. Tap **Hide** to remove the current card
from rotation; flip the **Backlog** switch to view hidden cards and **Restore**
them. This state is per-device and survives data updates.

## Files

| File                  | Purpose                                          |
| --------------------- | ------------------------------------------------ |
| `index.html`          | App shell / layout                               |
| `styles.css`          | Teal/sky palette matching the desktop app        |
| `app.js`              | All behaviour (flip, nav, search, jump, backlog) |
| `sw.js`               | Service worker — offline cache                   |
| `manifest.webmanifest`| Install metadata (name, icons, colours)          |
| `icon-192/512.png`    | App icons (generated)                            |
| `cards.json`          | **Generated** card data — do not hand-edit       |
