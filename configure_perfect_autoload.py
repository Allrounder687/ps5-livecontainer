import ftplib
import io

host = '192.168.0.208'
ftp = ftplib.FTP()
ftp.connect(host, 2121, timeout=10)
ftp.login()
print("[+] Connected to PS5 FTP")

# 1. Write /data/pldmgr/autoload.txt
autoload_lines = [
    "kstuff-lite_v1.10.elf",
    "nanoDNS_0.4.elf",
    "ftpsrv_v0.21.elf",
    "elfldr_v0.24.elf",
    "ShadowMountPlus_1.6beta16.elf",
    "elf-arsenal.elf"
]
autoload_content = "\n".join(autoload_lines) + "\n"
ftp.storbinary("STOR /data/pldmgr/autoload.txt", io.BytesIO(autoload_content.encode('utf-8')))
print("[+] Written /data/pldmgr/autoload.txt:")
for l in autoload_lines:
    print(f"    -> {l}")

# 2. Write /data/pldmgr/pldmgr_config.txt
pldmgr_config = (
    "AUTOLOAD_ENABLED=1\n"
    "LAST_REPOSITORY_UPDATE=1787198367\n"
    "AUTO_BROWSER_OPEN=0\n"
    "AUTOLOAD_DELAY=5\n"
    "KILL_DISC_PLAYER_ON_STARTUP=1\n"
    "SCAN_USB_PAYLOADS=1\n"
    "AUTO_INSTALL_APP=1\n"
    "MULTI_SOURCES_ENABLED=0\n"
)
ftp.storbinary("STOR /data/pldmgr/pldmgr_config.txt", io.BytesIO(pldmgr_config.encode('utf-8')))
print("[+] Configured /data/pldmgr/pldmgr_config.txt (AUTOLOAD_ENABLED=1, DELAY=5s, AUTO_BROWSER=0)")

# 3. Clean up manual.lst in ShadowMount if needed
ftp.storbinary("STOR /data/shadowmount/manual.lst", io.BytesIO(b"/data/homebrew/PPSA10595-app0\n/data/homebrew/PPSA02343-app0\n"))
print("[+] Configured /data/shadowmount/manual.lst for instant game mounting")

ftp.quit()
print("\n[+] Done! Autoloader sequence is now structured perfectly.")
