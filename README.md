# PS5 LiveContainer Framework

A native PlayStation 5 container host and in-memory dynamic runtime environment inspired by iOS LiveContainer.

---

## 🌟 Key Features

1. **In-Memory Dynamic ELF Relocator & Loader (`elf_loader.c`)**:
   - Parses ELF64 binaries (`x86_64-sie-ps5`), maps RWX memory pages, handles relocations (`R_X86_64_RELATIVE`, `R_X86_64_GLOB_DAT`, `R_X86_64_JUMP_SLOT`), and resolves dynamic symbols (`dlsym`).
2. **Crash Trap & Recovery Guard (`signal_guard.c`)**:
   - Intercepts fatal signals (`SIGSEGV`, `SIGBUS`, `SIGILL`, `SIGFPE`, `SIGABRT`) using an alternate signal stack and `sigsetjmp`/`siglongjmp`.
   - If guest homebrew crashes or dereferences NULL, the console **never reboots or loses jailbreak state**—LiveContainer catches the error, frees memory, and safely returns to the dashboard.
3. **Mobile & Desktop Web Dashboard (`http_server.c`)**:
   - Built-in HTTP micro-server running on **Port 8080** (`http://<PS5_IP>:8080`).
   - Drag-and-drop `.elf` uploads, 1-tap launcher, and real-time streaming console logs.
4. **VFS Path Sandboxing (`vfs_sandbox.c`)**:
   - Isolates app storage to `/data/containers/apps/<id>/data/` to prevent app data collisions.

---

## 📁 Directory Structure

```
ps5-livecontainer/
├── Dockerfile                  # Build environment (Clang-15 + ps5-payload-sdk)
├── Makefile                    # Multi-target Prospero Makefile
├── include/
│   ├── container_types.h       # State machine, slot structs, and constants
│   ├── elf_loader.h            # In-memory ELF64 relocator & loader
│   ├── signal_guard.h          # POSIX crash guard & stack recovery
│   ├── vfs_sandbox.h           # Isolated storage management
│   ├── http_server.h           # Web companion daemon & REST API
│   └── ps5_notify.h            # Toast notification helpers
├── src/
│   ├── main.c                  # Master daemon entry point & keepalive
│   ├── elf_loader.c            # Dynamic ELF loading implementation
│   ├── signal_guard.c          # Signal trap handling
│   ├── vfs_sandbox.c           # Path virtualization & registry persistence
│   ├── http_server.c           # HTTP daemon & endpoints
│   ├── web_ui_assets.h         # Responsive mobile-friendly Web UI
│   └── ps5_notify.c            # Notification dispatcher
├── test_payloads/
│   ├── hello_runner/           # Lightweight test payload
│   └── crash_catcher/          # Intentional SIGSEGV payload to test crash trap
└── scripts/
    ├── build.bat               # Windows Docker build script
    ├── build.sh                # Linux / macOS Docker build script
    └── deploy.py               # TCP payload sender (port 9021)
```

---

## 🚀 Building the Project

### Prerequisites
- [Docker Desktop](https://www.docker.com/) installed and running.

### Compilation
* **On Windows**: Run `scripts\build.bat`
* **On Linux / macOS**: Run `./scripts/build.sh`

This automatically builds:
- `ps5_livecontainer.elf` (The container host daemon)
- `test_payloads/hello_runner/eboot.elf`
- `test_payloads/crash_catcher/eboot.elf`

---

## 🎮 Deployment & Usage

### 1. Send the LiveContainer Daemon to your PS5
Ensure your PS5 is jailbroken with an ELF loader listening on port `9020` or `9021`:
```bash
python scripts/deploy.py --host <PS5_IP> --port 9021 --file ps5_livecontainer.elf
```

### 2. Access the Web Dashboard
Open any browser on your phone, tablet, or PC connected to the same Wi-Fi network:
```
http://<PS5_IP>:8080
```

### 3. Launch & Test Payloads
- **Hello Runner**: Tap **Launch** $\rightarrow$ Observe notification popup on your TV and output in the live log.
- **Crash Catcher**: Tap **Launch** $\rightarrow$ It triggers an intentional `SIGSEGV` crash $\rightarrow$ LiveContainer intercepts the crash, recovers execution safely, and keeps the console alive!
