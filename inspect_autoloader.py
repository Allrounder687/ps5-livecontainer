import ftplib
import io
import socket

host = '192.168.0.208'
print('=== Checking PS5 Network Connectivity ===')
for port in [2121, 9020, 9021, 8080, 8081]:
    s = socket.socket()
    s.settimeout(1.5)
    res = s.connect_ex((host, port))
    status = "OPEN" if res == 0 else f"CLOSED ({res})"
    print(f"Port {port}: {status}")
    s.close()

print('\n=== Connecting to FTP ===')
try:
    ftp = ftplib.FTP()
    ftp.connect(host, 2121, timeout=10)
    ftp.login()
    
    def read_path(path):
        print(f'\n--- {path} ---')
        buf = io.BytesIO()
        try:
            ftp.retrbinary(f'RETR {path}', buf.write)
            print(buf.getvalue().decode('utf-8', errors='replace').strip())
        except Exception as e:
            print(f'Error reading {path}: {e}')

    read_path('/data/pldmgr/pldmgr_config.txt')
    read_path('/data/pldmgr/autoload.txt')
    read_path('/data/etaHEN/config.ini')
    read_path('/data/shadowmount/config.ini')
    read_path('/data/shadowmount/manual.lst')
    
    print('\n--- Listing /data/pldmgr/payloads ---')
    ftp.retrlines('LIST /data/pldmgr/payloads')
    
    print('\n--- Listing /data/etaHEN/payloads ---')
    try:
        ftp.retrlines('LIST /data/etaHEN/payloads')
    except Exception as e:
        print(e)

    print('\n--- Listing /data/shadowmount/debug.log (last 20 lines) ---')
    try:
        buf = io.BytesIO()
        ftp.retrbinary('RETR /data/shadowmount/debug.log', buf.write)
        lines = buf.getvalue().decode('utf-8', errors='replace').splitlines()
        for l in lines[-20:]:
            print(l)
    except Exception as e:
        print(e)
        
    ftp.quit()
except Exception as e:
    print('FTP Error:', e)
