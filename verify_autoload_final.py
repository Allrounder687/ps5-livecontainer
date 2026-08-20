import ftplib
import io

host = '192.168.0.208'
ftp = ftplib.FTP()
ftp.connect(host, 2121, timeout=10)
ftp.login()

def check_file(path):
    print(f"=== {path} ===")
    buf = io.BytesIO()
    ftp.retrbinary(f"RETR {path}", buf.write)
    print(buf.getvalue().decode('utf-8', errors='replace').strip())

check_file('/data/pldmgr/autoload.txt')
print()
check_file('/data/pldmgr/pldmgr_config.txt')
print()
check_file('/data/shadowmount/manual.lst')

ftp.quit()
