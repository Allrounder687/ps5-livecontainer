# PS5 LiveContainer - Project Summary & Complete Changelog

A comprehensive log of all architectural research, implementations, debugging steps, compilation runs, and live deployments on the PlayStation 5 console (`192.168.0.208`).

---

## 📑 Table of Contents
1. [Core Concept & Architectural Decisions](#1-core-concept--architectural-decisions)
2. [Codebase & Subsystem Scaffolding](#2-codebase--subsystem-scaffolding)
3. [Toolchain & Docker Compilation](#3-toolchain--docker-compilation)
4. [PS5 Console Discovery & FTP Deployment](#4-ps5-console-discovery--ftp-deployment)
5. [Payload Manager vs. Native App0 Launch Mechanics](#5-payload-manager-vs-native-app0-launch-mechanics)
6. [Debugging "Cannot Start Game or App" & OS Constraints](#6-debugging-cannot-start-game-or-app--os-constraints)
7. [Current State & Summary of Artifacts](#7-current-state--summary-of-artifacts)

---

## 1. Core Concept & Architectural Decisions

* **Concept:** Building a PlayStation 5 counterpart to iOS **LiveContainer**—a single native host runner that dynamically executes guest homebrew binaries directly from memory with crash protection and remote web management.
* **Key Differentiator:** In standard PS5 homebrew workflows, if a payload crashes (e.g. `SIGSEGV` or `NULL` dereference), the entire host/WebKit process crashes and triggers a console reboot or lost jailbreak state. LiveContainer isolates execution inside dedicated `scePthread` worker threads wrapped in POSIX signal guards (`sigaction` + `sigsetjmp`/`siglongjmp`).
* **Commercial vs. Homebrew Games:**
  * **Homebrew Games & Emulators (Doom, SM64, RetroArch):** Can run directly inside the in-memory container sandbox without installation.
  * **Commercial Retail Games (God of War, Spider-Man):** Encrypted with Sony PFS/DRM requiring kernel `system_server` mounting; LiveContainer acts as a title launcher/switcher rather than an in-memory emulator for retail titles.

---

## 2. Codebase & Subsystem Scaffolding

A dedicated workspace was established at `ps5-livecontainer/` with the following modular architecture:

| Component | Source File | Functionality |
| :--- | :--- | :--- |
| **Data Models & State Machine** | `include/container_types.h` | Defines container slots, status flags (`IDLE`, `RUNNING`, `CRASHED`), memory footprints, and global context. |
| **In-Memory Dynamic ELF Relocator** | `src/elf_loader.c` | Parses ELF64 headers, maps RWX pages via `mmap`, processes dynamic relocations (`R_X86_64_RELATIVE`, `R_X86_64_GLOB_DAT`, `R_X86_64_JUMP_SLOT`), and resolves symbols via `dlsym()`. |
| **Signal Crash Guard** | `src/signal_guard.c` | Installs an alternate signal stack (`sigaltstack`) to trap `SIGSEGV`, `SIGBUS`, `SIGILL`, `SIGFPE`, `SIGABRT`, safely restoring stack execution upon guest crash without kernel panic. |
| **Storage Sandboxing** | `src/vfs_sandbox.c` | Virtualizes per-app storage directories under `/data/containers/apps/<id>/data/` and persists metadata to `containers.json`. |
| **Web Companion & REST Server** | `src/http_server.c` | Embedded HTTP daemon listening on **Port 8080** (`/api/status`, `/api/containers`, `/api/launch`, `/api/stop`, `/api/logs`). |
| **Cyberpunk Web Dashboard** | `src/web_ui_assets.h` | Embedded mobile/desktop HTML5/CSS/JS frontend with 1-tap launcher, drag-and-drop `.elf` uploader, and streaming log console. |
| **Notification Dispatcher** | `src/ps5_notify.c` | Dispatches on-screen toast notifications via `sceKernelSendNotificationRequest`. |
| **Standalone Notify Tool** | `tools/notify/main.c` | Standalone CLI/ELF notification utility maintaining a 3-second IPC persistence window for the notification daemon. |
| **Test Payload 1: Hello Runner** | `test_payloads/hello_runner/` | Lightweight guest payload to verify clean execution and TV popup feedback. |
| **Test Payload 2: Crash Catcher** | `test_payloads/crash_catcher/` | Intentionally triggers a `SIGSEGV` to test crash interception and rollback. |

---

## 3. Toolchain & Docker Compilation

* **Build Environment:** Utilized the existing local Docker image **`ps5-sdk:latest`** (ID: `d5749dfbb92b`) based on Ubuntu 22.04 with `clang-15`, `lld-15`, and John Törnblom's `ps5-payload-sdk`.
* **Fixes Applied during Compilation:**
  1. *Relocation Constants:* Defined missing fallback constants for `R_X86_64_JUMP_SLOT`, `R_X86_64_GLOB_DAT`, `R_X86_64_RELATIVE`, and `R_X86_64_64`.
  2. *Thread Library Linking:* Resolved `unable to find library -lScePthread` (pthread primitives on Prospero are integrated into `libkernel.so`).
  3. *Prospero Runtime Linking:* Linked full suite of system libraries:
     `-lkernel_sys -lkernel -lSceSystemService -lSceUserService -lSceVideoOut -lSceNet -lSceSsl -lSceHttp2`.
* **Compiled Artifacts:**
  * `ps5_livecontainer.elf` (~109 KB)
  * `test_payloads/hello_runner/eboot.elf` (~73 KB)
  * `test_payloads/crash_catcher/eboot.elf` (~72 KB)
  * `tools/notify/notify.elf` (~73 KB)

---

## 4. PS5 Console Discovery & FTP Deployment

* **Console Connection:** Automated deployment scripts connected to `192.168.0.208:2121` running `ftpsrv.elf v0.21`.
* **Discovered Installed Ecosystem:**
  * Exploits & HEN: `etaHEN 2.6B`, `kstuff-lite`
  * Mounters & Managers: `ShadowMount+ v1.6beta16`, `pldmgr v0.5.1`, `Itemzflow`, `elf-arsenal`
  * Existing Installed Homebrew: `PPSA99901-app0` ("IT Games"), `PPSA02343-app0` (UE4 game port)
* **Deployed Files:**
  * `/data/pldmgr/payloads/LiveContainer/LiveContainer.elf` + `.json`
  * `/data/notify.elf` and `/data/pldmgr/payloads/notify/notify.elf` + `.json`
  * `/data/containers/apps/org.ps5.hello/eboot.elf`
  * `/data/containers/apps/org.ps5.crashtrap/eboot.elf`

---

## 5. Payload Manager vs. Native App0 Launch Mechanics

* **Symptom:** When clicking "Launch" in Payload Manager, the UI showed "Launched", but nothing appeared on the TV screen and Port 8080 remained closed.
* **Root Cause:**
  * Payload Manager (`pldmgr`) does not inject ELF binaries into kernel memory directly; it acts as a client that relays `.elf` files over local TCP (`127.0.0.1:9021`) to an in-memory `elfldr` listener.
  * Port scans confirmed Port 9020 and 9021 were closed (no `elfldr` daemon was running in background RAM).
* **Resolution:** Transitioned the architecture to package LiveContainer as a **Native PS5 Homebrew Application (`app0`)** in `/data/homebrew/`, allowing the PS5 OS kernel and ShadowMount to mount and execute it as a standalone application.

---

## 6. Debugging "Cannot Start Game or App" & OS Constraints

When launched from the home screen, the console displayed *"Cannot start the game or app"*. Investigation of `ShadowMount` debug logs and working title `PPSA99901-app0` revealed four strict OS constraints:

1. **Title ID Format Violation:**
   * *Issue:* The PS5 OS kernel rejected the custom ID `LIVE00001`.
   * *Fix:* Formatted the Title ID strictly as `PPSA` + 5 digits (`PPSA99901` / `PPSA99902`) in `param.json` and directory naming.
2. **FreeBSD OS/ABI Header Validation:**
   * *Issue:* Clang standard output left bytes 7 & 8 as System V ABI (`0x00`). The PS5 Prospero loader requires FreeBSD ABI (`0x09`, `0x02`).
   * *Fix:* Injected `0x09, 0x02` into byte offset 7 & 8.
3. **FSELF (Fake-Signed ELF) Packaging (`make_fself.py`):**
   * *Issue:* The PS5 OS loader (`system_server`) strictly requires executables to be wrapped in a signed **SELF container** (`SELF_MAGIC = 0x1D3D154F`) with `npdrm_exec` program type and embedded `auth_info`. Raw ELFs are rejected at launch.
   * *Fix:* Ported flatz's `make_fself.py` to Python 3 (`scripts/make_fself.py`), converted `ps5_livecontainer.elf` into `eboot_fself.bin`, and deployed it as `eboot.bin` to `/data/homebrew/PPSA99901-app0/` and `PPSA99902-app0/`.
4. **Required Assets & Metadata:**
   * *Issue:* Missing `keystone`, `contentids.json`, and splash art (`pic0.png`, `pic1.png`, `icon0.png`).
   * *Fix:* Deployed the complete package structure with valid dummy `keystone` and matching `contentId` (`EP0001-PPSA99901_00-ITGAMES000000000` / `EP0001-PPSA99902_00-LIVECONTAINER000`).
5. **Duplicate Directory Cleanup:**
   * Cleaned up residual `LIVE00001-app0` directory over FTP.

---

## 7. Current State & Summary of Artifacts

* **Home Screen Status:** Successfully signed as **FSELF** (`npdrm_exec`) and deployed to `/data/homebrew/PPSA99901-app0/` and `PPSA99902-app0/`.
* **Project Directory Structure:**
  ```
  ps5-livecontainer/
  ├── Dockerfile                    # PS5 SDK toolchain container
  ├── Makefile                      # Prospero multi-target build script
  ├── README.md                     # Framework documentation
  ├── SUMMARY_AND_CHANGELOG.md      # This comprehensive log
  ├── include/
  │   ├── container_types.h         # State machine & data structures
  │   ├── elf_loader.h              # In-memory ELF loader header
  │   ├── signal_guard.h            # Crash protection header
  │   ├── vfs_sandbox.h             # Storage sandbox header
  │   ├── http_server.h             # Web companion daemon header
  │   └── ps5_notify.h              # Toast notification header
  ├── src/
  │   ├── main.c                    # Host daemon entrypoint & persistent file logger
  │   ├── elf_loader.c              # Pure-C dynamic ELF64 relocator
  │   ├── signal_guard.c            # POSIX signal trap handler
  │   ├── vfs_sandbox.c             # /data/containers/ isolation logic
  │   ├── http_server.c             # Socket listener & REST API
  │   ├── web_ui_assets.h           # Embedded HTML/CSS/JS frontend
  │   └── ps5_notify.c              # sceKernelSendNotificationRequest dispatcher
  ├── test_payloads/
  │   ├── hello_runner/             # Demo payload 1
  │   └── crash_catcher/            # Demo payload 2 (SIGSEGV trap test)
  ├── tools/
  │   └── notify/                   # Standalone notify.elf helper
  └── scripts/
      ├── build.bat / build.sh      # Automated Docker compilation
      ├── make_fself.py             # Python 3 FSELF signer (npdrm_exec)
      ├── upload_to_ps5.py          # FTP payload uploader
      └── deploy_ppsa.py            # Complete app0 packager
  ```
