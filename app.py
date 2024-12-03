import socket
import json
import threading
from minotaurx_hash import getPoWHash  # Thư viện xử lý thuật toán MinotaurX đã được build

class Miner:
    def __init__(self, pool_url, wallet, port, password, threads):
        """
        Khởi tạo lớp Miner.
        :param pool_url: Địa chỉ của pool.
        :param wallet: Địa chỉ ví.
        :param port: Cổng kết nối của pool.
        :param password: Mật khẩu (hoặc thông tin c=...).
        :param threads: Số luồng khai thác.
        """
        self.pool_url = pool_url
        self.wallet = wallet
        self.port = port
        self.password = password
        self.threads = threads
        self.connection = None
        self.job = None
        self.extranonce1 = None
        self.extranonce2_size = None
        self.difficulty_target = None  # Giá trị mục tiêu dựa trên độ khó nhận từ pool
        self.running = True

    def connect(self):
        """Kết nối tới pool khai thác."""
        try:
            self.connection = socket.create_connection((self.pool_url, self.port))
            print(f"Kết nối thành công tới {self.pool_url}:{self.port}")
        except Exception as e:
            print(f"Lỗi khi kết nối tới pool: {e}")
            self.running = False

    def subscribe(self):
        """Gửi yêu cầu đăng ký (subscribe) tới pool."""
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
                print("Đăng ký thành công. Nhận extranonce1 và extranonce2_size từ pool.")
        except Exception as e:
            print(f"Lỗi khi đăng ký: {e}")
            self.running = False

    def authorize(self):
        """Gửi yêu cầu xác thực (authorize) tới pool."""
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
        self.connection.sendall((json.dumps(data) + "\n").encode())

    def receive_json(self):
        """Nhận dữ liệu JSON từ pool."""
        try:
            response = self.connection.recv(1024).decode()
            for line in response.splitlines():
                return json.loads(line)
        except Exception as e:
            print(f"Lỗi khi nhận dữ liệu JSON: {e}")
            return None

    def handle_jobs(self):
        """Nhận và xử lý công việc mới từ pool."""
        while self.running:
            try:
                response = self.receive_json()
                if response and response.get("method") == "mining.notify":
                    self.job = response["params"]
                    self.difficulty_target = self.calculate_target(self.job[6])  # Tính target từ nbits
                    print(f"Nhận công việc mới: {self.job[0]}, Target: {self.difficulty_target}")
            except Exception as e:
                print(f"Lỗi khi nhận công việc: {e}")
                self.running = False

    def calculate_target(self, nbits):
        """Tính toán target từ nbits (compact format)."""
        nbits_int = int(nbits, 16)
        exponent = (nbits_int >> 24) & 0xFF
        coefficient = nbits_int & 0xFFFFFF
        target = coefficient * (2 ** (8 * (exponent - 3)))
        return target

    def mine(self, thread_id):
        """Thực hiện khai thác (tính toán hash)."""
        while self.running:
            if self.job:
                job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = self.job
                extranonce2 = f"{thread_id:0{self.extranonce2_size * 2}x}"
                coinbase = coinb1 + self.extranonce1 + extranonce2 + coinb2
                coinbase_hash_bin = getPoWHash(bytes.fromhex(coinbase))
                merkle_root = coinbase_hash_bin.hex()
                for branch in merkle_branch:
                    merkle_root = getPoWHash(bytes.fromhex(merkle_root + branch)).hex()
                blockheader = version + prevhash + merkle_root + nbits + ntime + "00000000"
                blockhash = getPoWHash(bytes.fromhex(blockheader)).hex()

                # So sánh blockhash với target
                if int(blockhash, 16) < self.difficulty_target:
                    print(f"[Thread {thread_id}] Đào được block! {blockhash}")
                    self.send_json({
                        "id": 4,
                        "method": "mining.submit",
                        "params": [self.wallet, job_id, extranonce2, ntime, "00000000"]
                    })
                else:
                    print(f"[Thread {thread_id}] Hash: {blockhash} không đạt yêu cầu.")

    def start(self):
        """Bắt đầu quá trình đào."""
        self.connect()
        if self.running:
            self.subscribe()
        if self.running:
            self.authorize()

        if self.running:
            # Tạo luồng nhận công việc
            threading.Thread(target=self.handle_jobs, daemon=True).start()

            # Tạo các luồng khai thác
            threads = []
            for i in range(self.threads):
                thread = threading.Thread(target=self.mine, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()


if __name__ == "__main__":
    pool = "minotaurx.na.mine.zpool.ca"
    wallet = "R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q"
    port = 7019
    password = "c=RVN"
    threads = 2

    miner = Miner(pool, wallet, port, password, threads)
    miner.start()
