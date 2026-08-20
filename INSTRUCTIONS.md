# 🎮 PS5 LiveContainer Framework: Complete User & Developer Guide

Welcome to the **PS5 LiveContainer Framework**, an in-memory homebrew ELF sandbox, runner, and companion manager for the PlayStation 5 (running `etaHEN` or compatible payload loaders).

---

## 📑 Table of Contents
1. [Overview & Architecture](#-overview--architecture)
2. [Prerequisites](#-prerequisites)
3. [Quick Start: Launching LiveContainer](#-quick-start-launching-livecontainer)
4. [Using the Web Dashboard](#-using-the-web-dashboard)
5. [Installing Guest Homebrew & Containers](#-installing-guest-homebrew--containers)
6. [Desktop Manager: `ps5_ftp_tauri`](#-desktop-manager-ps5_ftp_tauri)
7. [Developer Guide: Building Payloads for LiveContainer](#-developer-guide-building-payloads-for-livecontainer)
8. [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## 🧠 Overview & Architecture

### What LiveContainer Solves
Normally on the PS5, homebrew binaries suffer from three major roadblocks:
1. **The FSELF/App0 Wall:** Standard PS4 fake-signing tools do not generate native PS5 dashboard packages.
2. **The SDK Firmware Trap:** Default `crt1.o` runtimes contain hardcoded firmware offset tables that cause payloads to silently exit on modern firmwares.
3. **The Sandbox Jail Trap:** `elfldr` restores the `SceRedisServer` jail directory, making files written to `/data/` invisible over FTP unless jailbroken with root vnodes.

LiveContainer bypasses these restrictions by:
- Direct **`libkernel.sprx` syscall gadget** execution (`*(args[0]) + 0x0A`).
- Self-contained **VFS Sandboxing** under `/data/containers/apps/`.
- **Signal Guard Trap Handler:** Intercepting `SIGSEGV`, `SIGBUS`, and `SIGILL` to prevent console kernel panics when testing experimental code.
- Embedded **Glassmorphic Web UI Server** on Port **8081**.

---

## ⚙️ Prerequisites
- **Target Console:** PlayStation 5 running `etaHEN` (Firmware 3.xx - 8.xx supported).
- **Network Ports Active on PS5:**
  - `2121`: FTP Server (etaHEN `ftpsrv`)
  - `9021`: `elfldr` Payload Port
  - `8081`: LiveContainer Web Companion UI

---

## 🚀 Quick Start: Launching LiveContainer

You have three convenient ways to launch the LiveContainer daemon:

### Method 1: PS5 Dashboard Home Screen Icon
1. On your PS5 TV screen, select the **LiveContainer** (or `PPSA99910` / `PPSA02343`) icon.
2. Press **X** on your DualSense controller.
3. A toast notification will appear in the top-right corner of your TV: `🎮 LiveContainer Active & Running!`.
4. The background daemon is now active on Port 8081.

### Method 2: Auto-Boot with etaHEN
- The daemon executable is installed at `/data/etaHEN/payloads/livecontainer.elf`.
- Every time you run etaHEN on your PS5, LiveContainer starts in the background automatically.

### Method 3: 1-Click Injection via Desktop or Python
If you prefer manual injection from your PC:
```bash
python deploy_ui_8081.py
```

---

## 🌐 Using the Web Dashboard

Open any web browser on your phone, tablet, or PC connected to the same Wi-Fi network:

```
http://<YOUR_PS5_IP>:8081
```
*(Example: `http://192.168.0.208:8081`)*

### Features Available in the Web UI:
- **Container Slot Cards:** View all installed games/emulators and their live status (`READY`, `RUNNING`, `CRASHED`).
- **1-Tap Launch Controls:** Trigger guest payload execution directly from your browser.
- **Live System Console:** Real-time stream of host engine logs, sandbox paths, and crash telemetry.

---

## 📦 Installing Guest Homebrew & Containers

Each homebrew container resides in an isolated folder under `/data/containers/apps/<app_id>/`:

```text
/data/containers/
├── containers.json             # Slot metadata & registry
└── apps/
    ├── hello_runner/
    │   ├── eboot.elf           # Native PS5 executable
    │   └── data/               # App-specific persistent storage
    └── doom/
        ├── eboot.elf
        ├── doom1.wad
        └── data/
```

### Adding a New Container Slot:
1. Connect to your PS5 over FTP (`Port 2121`).
2. Create a folder: `/data/containers/apps/<your_app_id>/`.
3. Upload your compiled payload as `eboot.elf` into that directory.
4. Add an entry to `/data/containers/containers.json`:
   ```json
   {
     "id": "org.ps5.doom",
     "name": "DOOM PS5",
     "path": "/data/containers/apps/doom/eboot.elf",
     "state": "READY"
   }
   ```
5. Refresh `http://<PS5_IP>:8081` — your new container will appear immediately.

---

## 💻 Desktop Manager: `ps5_ftp_tauri`

For a complete desktop management experience with Drag & Drop, Dual-Pane FTP, and 1-Click Payload Injection:

1. Open `C:\Users\Achie\Documents\antigravity\ps5_ftp_tauri`.
2. Run `npm run tauri dev`.
3. Use the new **LIVECONTAINER** tab to:
   - Inject `.elf` payloads to Port 9021 with 1 click.
   - Install `.zip`, `.rar`, or `.elf` packages directly into LiveContainer slots.
   - Jump straight to the Web Dashboard.

---

## 🛠️ Developer Guide: Building Payloads for LiveContainer

### 1. The Syscall Rule
Do **not** execute direct raw `syscall` opcodes (`0x0F, 0x05`) from payload memory pages. Use the `libkernel` gadget passed in `args[0]`:
```c
/* rdi points to payload_args_t* */
/* *(args[0]) + 0x0A = 'syscall; ret' inside libkernel.sprx */
```

### 2. Jailbreak Sandbox Escape
Always borrow root and jail vnodes from PID 1 on startup:
```c
intptr_t root = kernel_get_proc_rootdir(1);
intptr_t jail = kernel_get_proc_jaildir(1);
if (root) kernel_set_proc_rootdir(getpid(), root);
if (jail) kernel_set_proc_jaildir(getpid(), jail);
```

### 3. ELF Stripping
Always strip symbols before sending to `elfldr`:
```bash
strip --strip-all my_payload.elf
```

---

## ❓ Troubleshooting & FAQs

### Q: Why do I get a connection refused on port 8081?
**A:** Ensure `elfldr` is active on Port 9021, or launch the LiveContainer icon on your PS5 home screen.

### Q: Does LiveContainer persist after a PS5 reboot?
**A:** LiveContainer is placed in `/data/etaHEN/payloads/livecontainer.elf`, so etaHEN starts it automatically on boot. If needed, you can also launch it via the PS5 TV dashboard icon or desktop app with 1 click.

### Q: Can my guest payload crash the entire console?
**A:** LiveContainer includes a built-in **Signal Guard** that traps fatal signals (`SIGSEGV`, `SIGBUS`, `SIGILL`) on an alternate stack, preventing kernel panics and preserving your jailbreak state.
