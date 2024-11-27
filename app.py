import socket
import threading
import struct
import json
from minotaurx_hash import getPoWHash  # Thư viện hashing của bạn

def mine(pool, port, wallet, password, threads):
    def connect_to_pool():
        try:
            sock = socket.create_connection((pool, port))
            sock.settimeout(10)
            print(f"Kết nối thành công đến pool: {pool}:{port}")
            return sock
        except Exception as e:
            print(f"Lỗi kết nối tới pool: {e}")
            return None

    def send_to_pool(sock, message):
        try:
            print(f"[DEBUG] Gửi tới pool: {message}")
            sock.sendall((message + "\n").encode())
        except Exception as e:
            print(f"Lỗi gửi dữ liệu tới pool: {e}")

    def receive_from_pool(sock):
        try:
            response = sock.recv(1024).decode()
            print(f"[DEBUG] Nhận từ pool: {response}")
            return response
        except Exception as e:
            print(f"Lỗi nhận dữ liệu từ pool: {e}")
            return ""

    def worker(sock, thread_id):
        while True:
            # Nhận công việc từ pool
            response = receive_from_pool(sock)
            if not response:
                print(f"[Thread-{thread_id}] Không nhận được dữ liệu từ pool.")
                break
            
            try:
                # Sử dụng json.loads để xử lý chuỗi JSON
                data = json.loads(response)
                job_id = data.get("job_id")
                prev_hash = data.get("prev_hash")
                difficulty = data.get("difficulty", 0xFFFF)
                nonce = 0

                if not job_id or not prev_hash:
                    print(f"[Thread-{thread_id}] Job không hợp lệ: {data}")
                    continue

                print(f"[Thread-{thread_id}] Nhận job: {job_id}, difficulty: {difficulty}")

                # Thực hiện hashing và tìm nonce hợp lệ
                while True:
                    nonce_bytes = struct.pack("<I", nonce)
                    header = prev_hash + nonce_bytes.hex()
                    hash_result = getPoWHash(bytes.fromhex(header)).hex()

                    # Kiểm tra kết quả
                    if int(hash_result, 16) < difficulty:
                        print(f"[Thread-{thread_id}] Work found! Nonce: {nonce}, Hash: {hash_result}")
                        submit = json.dumps({
                            "method": "submit",
                            "params": {
                                "id": job_id,
                                "nonce": nonce,
                                "hash": hash_result
                            }
                        })
                        send_to_pool(sock, submit)
                        break

                    nonce += 1
                    if nonce > 2**32 - 1:  # Nếu nonce vượt giới hạn
                        break
            except json.JSONDecodeError as e:
                print(f"[Thread-{thread_id}] Lỗi xử lý JSON: {e}")
            except Exception as e:
                print(f"[Thread-{thread_id}] Lỗi xử lý công việc: {e}")

    # Tạo kết nối tới pool
    sock = connect_to_pool()
    if not sock:
        return

    # Gửi yêu cầu subscribe và authorize
    subscribe_message = '{"id":1,"method":"mining.subscribe","params":[]}'
    authorize_message = json.dumps({
        "id": 2,
        "method": "mining.authorize",
        "params": [wallet, password]
    })

    send_to_pool(sock, subscribe_message)
    send_to_pool(sock, authorize_message)

    # Tạo các thread để đào
    thread_list = []
    for i in range(threads):
        t = threading.Thread(target=worker, args=(sock, i))
        thread_list.append(t)
        t.start()

    for t in thread_list:
        t.join()

if __name__ == "__main__":
    # Cấu hình mặc định
    pool = "minotaurx.na.mine.zpool.ca"
    port = 7019
    wallet = "R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q"
    password = "c=RVN"
    threads = int(input("Nhập số lượng threads: "))

    print(f"Đang kết nối tới pool {pool}:{port} với ví {wallet}, mật khẩu {password} và {threads} threads...")
    mine(pool, port, wallet, password, threads)
