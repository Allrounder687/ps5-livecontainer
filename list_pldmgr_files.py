import ftplib

host = '192.168.0.208'
ftp = ftplib.FTP()
ftp.connect(host, 2121, timeout=10)
ftp.login()

subdirs = []
ftp.retrlines('LIST /data/pldmgr/payloads', subdirs.append)

print("=== Payload Files in /data/pldmgr/payloads ===")
for line in subdirs:
    parts = line.split()
    if len(parts) >= 9:
        name = parts[8]
        if name not in ['.', '..'] and line.startswith('d'):
            print(f"\n[{name}]")
            try:
                flist = []
                ftp.retrlines(f"LIST /data/pldmgr/payloads/{name}", flist.append)
                for f in flist:
                    print("  ", f)
            except Exception as e:
                print("  error:", e)

ftp.quit()
