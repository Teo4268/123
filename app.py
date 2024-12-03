import socket
import json
import struct
import threading
import time
from minotaurx_hash import getPoWHash  # Thư viện bạn đã build

# Cấu hình mining
POOL = "stratum+tcp://minotaurx.na.mine.zpool.ca"  # Địa chỉ pool
PORT = 7019  # Port của pool
WALLET = "R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q"
PASSWORD = "c=RVN"  # Mật khẩu (mặc định là "x")
THREADS = 4  # Số lượng threads

# Hàm kết nối tới mining pool
def connect_to_pool():
    try:
        s = socket.create_connection((POOL.split("//")[1], PORT))
        return s
    except Exception as e:
        print(f"Không thể kết nối tới pool: {e}")
        return None

# Gửi dữ liệu tới pool
def send_to_pool(socket, data):
    try:
        socket.sendall((json.dumps(data) + "\n").encode())
    except Exception as e:
        print(f"Lỗi khi gửi dữ liệu tới pool: {e}")

# Nhận dữ liệu từ pool
def receive_from_pool(socket):
    try:
        response = socket.recv(1024).decode()
        return [json.loads(line) for line in response.splitlines() if line.strip()]
    except Exception as e:
        print(f"Lỗi khi nhận dữ liệu từ pool: {e}")
        return []

# Hàm giải nonce
def mine(job_id, prev_hash, target, extranonce1, extranonce2_size):
    extranonce2 = 0
    while True:
        extranonce2_bin = struct.pack("<I", extranonce2)
        header = prev_hash + extranonce1 + extranonce2_bin.hex()
        hash_result = getPoWHash(bytes.fromhex(header))
        if int(hash_result.hex(), 16) < target:
            return extranonce2, hash_result.hex()
        extranonce2 += 1

# Hàm thực thi mining
def mining_thread(pool_socket, job, target, extranonce1, extranonce2_size):
    while True:
        try:
            extranonce2, valid_hash = mine(
                job["job_id"], job["prev_hash"], target, extranonce1, extranonce2_size
            )
            submit_data = {
                "id": 4,
                "method": "mining.submit",
                "params": [WALLET, job["job_id"], extranonce2, valid_hash],
            }
            send_to_pool(pool_socket, submit_data)
            print(f"Đã gửi kết quả: {valid_hash}")
        except Exception as e:
            print(f"Lỗi trong thread mining: {e}")

# Khởi chạy chương trình
def start_mining():
    pool_socket = connect_to_pool()
    if not pool_socket:
        return

    # Đăng nhập vào pool
    login_data = {
        "id": 1,
        "method": "mining.subscribe",
        "params": [WALLET, PASSWORD],
    }
    send_to_pool(pool_socket, login_data)

    # Lắng nghe phản hồi
    responses = receive_from_pool(pool_socket)
    for response in responses:
        if "error" in response and response["error"]:
            print(f"Lỗi từ pool: {response['error']}")
            return

        if response.get("result"):
            extranonce1 = response["result"][1]
            extranonce2_size = response["result"][2]

    # Lấy thông tin job đầu tiên
    while True:
        responses = receive_from_pool(pool_socket)
        for response in responses:
            if response.get("method") == "mining.notify":
                job = {
                    "job_id": response["params"][0],
                    "prev_hash": response["params"][1],
                    "coinb1": response["params"][2],
                    "coinb2": response["params"][3],
                }
                target = int(response["params"][6], 16)

                # Chạy các thread
                for _ in range(THREADS):
                    threading.Thread(
                        target=mining_thread,
                        args=(pool_socket, job, target, extranonce1, extranonce2_size),
                    ).start()

if __name__ == "__main__":
    start_mining()
