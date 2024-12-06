import socket
import json
import time
from binascii import hexlify, unhexlify
import minotaurx_hash

# Cấu hình kết nối
POOL_ADDRESS = "minotaurx.na.mine.zpool.ca"
POOL_PORT = 7019
WALLET_ADDRESS = "R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q"
PASSWORD = "c=RVN"
LOG_FILE = "miner_error.log"

# Kết nối socket def connect_to_pool():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((POOL_ADDRESS, POOL_PORT))
        print(f"[INFO] Kết nối thành công tới pool {POOL_ADDRESS}:{POOL_PORT}")
        return sock
    except Exception as e:
        log_error(f"Không thể kết nối tới pool: {e}")
        raise

def send_json(sock, data):
    message = json.dumps(data) + "\n"
    sock.sendall(message.encode("utf-8"))

def receive_json(sock):
    buffer = b""
    while True:
        chunk = sock.recv(1024)
        if not chunk:
            break
        buffer += chunk
        if b"\n" in buffer:
            break
    return json.loads(buffer.decode("utf-8"))

# Log lỗi def log_error(message):
    with open(LOG_FILE, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

# Đào def mine():
    sock = connect_to_pool()
    
    # Gửi yêu cầu đăng nhập tới pool
    login_request = {
        "id": 1,
        "method": "mining.subscribe",
        "params": []
    }
    send_json(sock, login_request)
    response = receive_json(sock)
    print("[INFO] Phản hồi subscribe:", response)

    authorize_request = {
        "id": 2,
        "method": "mining.authorize",
        "params": [WALLET_ADDRESS, PASSWORD]
    }
    send_json(sock, authorize_request)
    response = receive_json(sock)
    print("[INFO] Phản hồi authorize:", response)

    # Lặp để nhận công việc và gửi kết quả while True:
        job_request = receive_json(sock)
        if "method" in job_request and job_request["method"] == "mining.notify":
            _, job_id, prev_hash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = job_request["params"]

            print(f"[INFO] Nhận công việc mới: Job ID {job_id}")
            print("[INFO] Băm block header...")
            
            # Băm dữ liệu
            header = (prev_hash + coinb1 + coinb2).encode('utf-8')
