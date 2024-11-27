import socket
import threading
import time
import struct
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
            sock.sendall((message + "\n").encode())
        except Exception as e:
            print(f"Lỗi gửi dữ liệu tới pool: {e}")

    def receive_from_pool(sock):
        try:
            response = sock.recv(1024).decode()
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
                data = eval(response)  # Pool gửi JSON (hoặc chuỗi tương tự)
                job_id = data["job_id"]
                prev_hash = data["prev_hash"]
                nonce = 0
                difficulty = data["difficulty"]
                print(f"[Thread-{thread_id}] Nhận job: {job_id}, difficulty: {difficulty}")

                # Thực hiện hashing và tìm nonce hợp lệ
                while True:
                    nonce_bytes = struct.pack("<I", nonce)
                    header = prev_hash + nonce_bytes.hex()
                    hash_result = getPoWHash(bytes.fromhex(header)).hex()

                    # Kiểm tra kết quả
                    if int(hash_result, 16) < difficulty:
                        print(f"[Thread-{thread_id}] Work found! Nonce: {nonce}, Hash: {hash_result}")
                        submit = f'{{"method": "submit", "params": {{"id": "{job_id}", "nonce": {nonce}, "hash": "{hash_result}"}}}}'
                        send_to_pool(sock, submit)
                        break

                    nonce += 1
                    if nonce > 2**32 - 1:  # Nếu nonce vượt giới hạn
                        break
            except Exception as e:
                print(f"[Thread-{thread_id}] Lỗi xử lý công việc: {e}")

    # Tạo kết nối tới pool
    sock = connect_to_pool()
    if not sock:
        return

    # Gửi thông tin đăng nhập tới pool
    login_message = f'{{"method": "login", "params": {{"login": "{wallet}", "pass": "{password}"}}}}'
    send_to_pool(sock, login_message)
    print("Đã gửi thông tin đăng nhập tới pool.")

    # Tạo các thread để đào
    thread_list = []
    for i in range(threads):
        t = threading.Thread(target=worker, args=(sock, i))
        thread_list.append(t)
        t.start()

    for t in thread_list:
        t.join()

if __name__ == "__main__":
    pool = input("Nhập địa chỉ pool (ví dụ: minotaurx.na.mine.zpool.ca): ")
    port = int(input("Nhập port của pool (ví dụ: 7019): "))
    wallet = input("Nhập địa chỉ ví của bạn: ")
    password = input("Nhập mật khẩu (password, ví dụ: x): ")
    threads = int(input("Nhập số lượng threads: "))

    print(f"Đang kết nối tới pool {pool}:{port} với ví {wallet}, mật khẩu {password} và {threads} threads...")
    mine(pool, port, wallet, password, threads)
