import socket
import json
import random
import struct
import threading
import time
import minotaurx_hash as x  # Đảm bảo bạn đã cài đặt thư viện này

class Miner(threading.Thread):
    def __init__(self, pool_url, wallet, port, password, threads):
        super().__init__()
        self.pool_url = pool_url
        self.wallet = wallet
        self.port = port
        self.password = password
        self.threads = threads
        self.connection = None
        self.job = None
        self.extranonce1 = None
        self.extranonce2_size = None
        self.target = None
        self.difficulty = None
        self.running = True
        self.id = None  # ID để quản lý phiên làm việc

    def connect(self):
        """Kết nối tới pool."""
        try:
            self.connection = socket.create_connection((self.pool_url, self.port))
            print(f"Kết nối thành công tới {self.pool_url}:{self.port}")
        except Exception as e:
            print(f"Lỗi khi kết nối tới pool: {e}")
            self.running = False

    def subscribe(self):
        """Gửi yêu cầu subscribe tới pool."""
        try:
            self.send_json({
                "id": 1,
                "method": "mining.subscribe",
                "params": []
            })
            response = self.receive_json()
            if response and "result" in response:
                self.extranonce1 = response["result"][1]
                self.extranonce2_size = response["result"][2]
                print("Đăng ký thành công.")
            else:
                print("Lỗi khi đăng ký: Dữ liệu trả về không hợp lệ.")
                self.running = False
        except Exception as e:
            print(f"Lỗi khi đăng ký: {e}")
            self.running = False

    def authorize(self):
        """Gửi yêu cầu đăng nhập (authorize)."""
        try:
            self.send_json({
                "id": 2,
                "method": "mining.authorize",
                "params": [self.wallet, self.password]
            })
            response = self.receive_json()
            if response and response.get("result", False):
                print("Đăng nhập thành công.")
            else:
                print("Lỗi khi đăng nhập.")
                self.running = False
        except Exception as e:
            print(f"Lỗi khi đăng nhập: {e}")
            self.running = False

    def send_json(self, data):
        """Gửi dữ liệu JSON tới pool."""
        try:
            self.connection.sendall((json.dumps(data) + "\n").encode())
        except Exception as e:
            print(f"Lỗi khi gửi dữ liệu: {e}")
            self.running = False

    def receive_json(self):
        """Nhận dữ liệu JSON từ pool."""
        try:
            response = self.connection.recv(4096).decode()
            for line in response.splitlines():
                return json.loads(line)
        except Exception as e:
            print(f"Lỗi khi nhận dữ liệu: {e}")
            return None

    def set_difficulty(self, difficulty):
        """Cập nhật độ khó và target."""
        try:
            difficulty = int(difficulty, 16)  # Chuyển từ hex sang số nguyên
            self.difficulty = difficulty

            # Tính toán lại target dựa trên độ khó
            if difficulty > 0:
                target = 2 ** (256 - difficulty)
                self.target = f"{target:064x}"
                print(f"Cập nhật độ khó: {self.difficulty}, target: {self.target}")
            else:
                print("Độ khó không hợp lệ!")
        except ValueError:
            print(f"Lỗi: Độ khó '{difficulty}' không hợp lệ. Phải là chuỗi hex hợp lệ.")

    def handle_jobs(self):
        """Nhận công việc mới từ pool và bắt đầu đào."""
        while self.running:
            try:
                response = self.receive_json()
                if response and response.get("method") == "mining.notify":
                    self.job = response["params"]
                    if self.job:
                        print(f"Nhận công việc mới: {self.job[0]}")
                        # Cập nhật lại độ khó và target từ công việc
                        difficulty = self.job[1]  # Cập nhật đúng vị trí chứa độ khó
                        self.set_difficulty(difficulty)

                        # Thực hiện đào (mining)
                        job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime = self.job
                        self.mine(job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime)
                    else:
                        print("Công việc không hợp lệ.")
                        self.running = False
                else:
                    print(f"Phản hồi không hợp lệ hoặc không phải 'mining.notify': {response}")
            except Exception as e:
                print(f"Lỗi khi nhận công việc: {e}")
                self.running = False

    def mine(self, job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime):
        """Tính toán Proof of Work và gửi kết quả tới pool."""
        extranonce2 = self.generate_extranonce2()
        merkle_root = self.calculate_merkle_root(extranonce2)
        header = self.create_header(prevhash, merkle_root, version, nbits, ntime)
        
        for nonce in range(0, 2**32):
            pow_hash = x.getPoWHash(header + struct.pack("<I", nonce))  # Tính toán PoW hash
            if int(pow_hash, 16) < int(self.target, 16):
                # Nếu hash nhỏ hơn target, gửi kết quả về pool
                result = {
                    "id": job_id,
                    "extranonce2": extranonce2,
                    "ntime": str(ntime),
                    "nonce": struct.pack("<I", nonce)[::-1].hex()
                }
                self.send_json({
                    "id": 3,
                    "method": "mining.submit",
                    "params": [self.wallet, job_id, extranonce2, str(ntime), struct.pack("<I", nonce)[::-1].hex()]
                })
                print(f"Đã gửi kết quả cho pool: {result}")
                break

    def generate_extranonce2(self):
        """Tạo extranonce2 cho công việc."""
        return f"{random.randint(0, 2**(8 * self.extranonce2_size) - 1):0{self.extranonce2_size * 2}x}"

    def calculate_merkle_root(self, extranonce2):
        """Tính toán merkle root từ coinb1, extranonce1, extranonce2 và coinb2."""
        # Sử dụng merkle branches để tính toán merkle root
        data = coinb1 + self.extranonce1 + extranonce2 + coinb2
        for branch in merkle_branches:
            data = x.getPoWHash(data + branch)
        return data

    def create_header(self, prevhash, merkle_root, version, nbits, ntime):
        """Tạo header cho việc tính toán PoW."""
        return struct.pack("<I", version) + bytes.fromhex(prevhash) + bytes.fromhex(merkle_root) + struct.pack("<I", ntime) + struct.pack("<I", nbits)

    def run(self):
        """Chạy miner."""
        self.connect()
        if not self.running:
            return

        self.subscribe()
        if not self.running:
            return

        self.authorize()
        if not self.running:
            return

        self.handle_jobs()


# Chạy chương trình
if __name__ == "__main__":
    pool_url = "minotaurx.na.mine.zpool.ca"  # Địa chỉ pool
    wallet = "R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q"  # Ví của bạn
    port = 7019  # Port của pool
    password = "c=RVN"  # Password
    threads = 2  # Số luồng

    miner = Miner(pool_url, wallet, port, password, threads)
    miner.start()
