import socket
import threading
import struct
import json
import time
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
            # Nhận dữ liệu từ pool
            response = sock.recv(4096).decode()
            if not response:
                raise ValueError("Dữ liệu nhận được rỗng từ pool")
            print(f"[DEBUG] Nhận từ pool: {response}")

            # Phân tách từng JSON nếu có nhiều dòng
            messages = response.strip().split("\n")
            return messages
        except Exception as e:
            print(f"Lỗi nhận dữ liệu từ pool: {e}")
            return []

    def worker(sock, thread_id):
        while True:
            responses = receive_from_pool(sock)
            if not responses:
                print(f"[Thread-{thread_id}] Không nhận được dữ liệu từ pool.")
                time.sleep(1)  # Chờ 1 giây trước khi thử lại
                continue
            
            for response in responses:
                try:
                    # Xử lý từng JSON riêng lẻ
                    data = json.loads(response)
                    
                    # Kiểm tra tính hợp lệ của công việc
                    if "method" in data and data["method"] == "mining.notify":
                        params = data.get("params", [])
                        if len(params) < 3:
                            print(f"[Thread-{thread_id}] Công việc từ pool không hợp lệ: {data}")
                            continue

                        job_id, prev_hash, difficulty = params[0], params[1], int(params[2], 16)
                        print(f"[Thread-{thread_id}] Nhận job: {job_id}, difficulty: {difficulty}")

                        # Thực hiện hashing và tìm nonce hợp lệ
                        nonce = 0
                        while True:
                            nonce_bytes = struct.pack("<I", nonce)
                            header = prev_hash + nonce_bytes.hex()
                            hash_result = getPoWHash(bytes.fromhex(header)).hex()

                            if int(hash_result, 16) < difficulty:
                                print(f"[Thread-{thread_id}] Work found! Nonce: {nonce}, Hash: {hash_result}")
                                submit = json.dumps({
                                    "id": 4,
                                    "method": "mining.submit",
                                    "params": [wallet, job_id, nonce, hash_result]
                                })
                                send_to_pool(sock, submit)
                                break

                            nonce += 1
                            if nonce > 2**32 - 1:  # Nếu nonce vượt giới hạn
                                break
                    else:
                        print(f"[Thread-{thread_id}] Bỏ qua thông điệp không phải công việc: {data}")
                except json.JSONDecodeError as e:
                    print(f"[Thread-{thread_id}] Lỗi xử lý JSON: {response}, lỗi: {e}")
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
