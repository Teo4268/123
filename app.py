import socket
import json
import threading
import time
from minotaurx_hash import getPoWHash  # Thư viện đã build

class Miner:
    def __init__(self, pool_url, wallet, port, password, threads):
        self.pool_url = pool_url.replace("stratum+tcp://", "")  # Loại bỏ tiền tố giao thức
        self.wallet = wallet
        self.port = port
        self.password = password
        self.threads = threads
        self.connection = None
        self.job = None
        self.extranonce1 = None
        self.extranonce2_size = None
        self.difficulty = None  # Để độ khó động
        self.running = True
        self.hashes_per_second = 0  # Biến lưu trữ hashrate
        self.total_hashes = 0  # Tổng số hashes đã tính

    def connect(self):
        """Kết nối tới pool và xử lý lại nếu kết nối bị mất"""
        while self.running:
            try:
                self.connection = socket.create_connection((self.pool_url, self.port))
                print(f"Kết nối thành công tới {self.pool_url}:{self.port}")
                break  # Nếu kết nối thành công, thoát khỏi vòng lặp
            except (socket.error, ConnectionError) as e:
                print(f"Lỗi khi kết nối tới pool: {e}. Thử lại trong 5 giây...")
                time.sleep(5)  # Thử lại sau 5 giây nếu gặp lỗi

    def subscribe(self):
        """Gửi yêu cầu subscribe tới pool"""
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
        except Exception as e:
            print(f"Lỗi khi đăng ký: {e}")
            self.running = False

    def authorize(self):
        """Gửi yêu cầu đăng nhập (authorize)"""
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
        """Gửi dữ liệu JSON tới pool và xử lý nếu bị mất kết nối"""
        try:
            self.connection.sendall((json.dumps(data) + "\n").encode())
        except (BrokenPipeError, socket.error) as e:
            print(f"Lỗi khi gửi dữ liệu: {e}. Thử kết nối lại...")
            self.connection.close()  # Đóng kết nối cũ
            self.connect()  # Tự động kết nối lại
            self.send_json(data)  # Gửi lại dữ liệu sau khi kết nối lại

    def receive_json(self):
        """Nhận dữ liệu JSON từ pool"""
        response = self.connection.recv(1024).decode()
        for line in response.splitlines():
            return json.loads(line)

    def handle_jobs(self):
        """Nhận công việc mới từ pool"""
        while self.running:
            try:
                response = self.receive_json()
                if response and response.get("method") == "mining.notify":
                    self.job = response["params"]
                    self.difficulty = int(self.job[7], 16) / (2**32)  # Chuyển đổi độ khó thành float
                    print(f"Nhận công việc mới: {self.job[0]} với độ khó {self.difficulty}")
            except Exception as e:
                print(f"Lỗi khi nhận công việc: {e}")
                self.running = False

    def mine(self, thread_id):
        """Thực hiện tính toán hash"""
        nonce = 0  # Bắt đầu từ nonce = 0
        start_time = time.time()  # Lấy thời gian bắt đầu
        hashes_this_cycle = 0  # Biến đếm số hash trong vòng này

        while self.running:
            if self.job and self.difficulty:
                job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = self.job
                extranonce2 = f"{thread_id:0{self.extranonce2_size * 2}x}"
                coinbase = coinb1 + self.extranonce1 + extranonce2 + coinb2
                coinbase_hash_bin = getPoWHash(bytes.fromhex(coinbase))
                merkle_root = coinbase_hash_bin.hex()

                # Tính toán merkle root
                for branch in merkle_branch:
                    merkle_root = getPoWHash(bytes.fromhex(merkle_root + branch)).hex()

                # Xây dựng blockheader: Phiên bản + previous block hash + merkle root + nbits + ntime + nonce
                blockheader = version + prevhash + merkle_root + nbits + ntime + f"{nonce:08x}"

                # Tính toán block hash
                blockhash = getPoWHash(bytes.fromhex(blockheader))

                # So sánh blockhash với độ khó
                block_hash_int = int(blockhash.hex(), 16)

                # In ra thông tin mỗi khi nonce không hợp lệ
                print(f"Block Hash: {blockhash.hex()} - Hash Int: {block_hash_int} - Difficulty: {self.difficulty}")

                # So sánh blockhash với độ khó
                if block_hash_int < self.difficulty * (2**256):
                    print(f"[Thread {thread_id}] Đào được block hợp lệ! {blockhash.hex()}")
                    self.send_json({
                        "id": 4,
                        "method": "mining.submit",
                        "params": [self.wallet, job_id, extranonce2, ntime, f"{nonce:08x}"]
                    })
                    # Không dừng lại, tiếp tục đào
                    nonce += 1

                hashes_this_cycle += 1  # Đếm số hash trong vòng này

            nonce += 1  # Tăng nonce sau mỗi vòng lặp

            # Tính toán hashrate mỗi 10 giây
            if time.time() - start_time >= 10:
                self.hashes_per_second = hashes_this_cycle / 10
                self.total_hashes += hashes_this_cycle
                print(f"Hashrate: {self.hashes_per_second:.2f} H/s | Tổng hash đã tính: {self.total_hashes}")
                start_time = time.time()  # Reset thời gian bắt đầu
                hashes_this_cycle = 0  # Reset đếm hash

    def start(self):
        """Bắt đầu đào coin"""
        self.connect()
        if self.running:
            self.subscribe()
        if self.running:
            self.authorize()

        if self.running:
            # Chạy luồng nhận công việc
            threading.Thread(target=self.handle_jobs, daemon=True).start()
            # Tạo các luồng đào
            threads = []
            for i in range(self.threads):
                thread = threading.Thread(target=self.mine, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()


if __name__ == "__main__":
    # Thông số pool, ví, port đã được gán sẵn
    pool = "minotaurx.na.mine.zpool.ca"
    wallet = "R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q"
    port = 7019
    password = "c=RVN"  # Bạn có thể thay đổi mật khẩu nếu cần
    threads = 1  # Sử dụng 1 luồng đào

    miner = Miner(pool, wallet, port, password, threads)
    miner.start()
