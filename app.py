import hashlib
import time
import struct
import json
import socket

from minotaurx_hash import getPowHash  # Nhớ rằng bạn đã cài thư viện này từ file C++

class Miner:
    def __init__(self, wallet, pool_url, pool_port, threads=1):
        self.wallet = wallet
        self.pool_url = pool_url
        self.pool_port = pool_port
        self.threads = threads
        self.extranonce1 = None
        self.extranonce2_size = 4  # Thường là 4 bytes
        self.difficulty = 1  # Mặc định độ khó
        self.running = True
        self.job = None
        self.socket = self.connect_to_pool()

    def connect_to_pool(self):
        """Kết nối tới pool qua Stratum"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self.pool_url, self.pool_port))
            print(f"Kết nối tới pool: {self.pool_url}:{self.pool_port} thành công!")
            return s
        except Exception as e:
            print(f"Lỗi khi kết nối tới pool: {e}")
            self.running = False
            return None

    def send_json(self, data):
        """Gửi dữ liệu JSON tới pool"""
        if self.socket:
            try:
                message = json.dumps(data) + "\n"
                self.socket.sendall(message.encode('utf-8'))
            except Exception as e:
                print(f"Lỗi khi gửi dữ liệu: {e}")

    def receive_json(self):
        """Nhận dữ liệu JSON từ pool"""
        if self.socket:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if data:
                    return json.loads(data)
            except Exception as e:
                print(f"Lỗi khi nhận dữ liệu: {e}")
        return None

    def handle_jobs(self):
        """Nhận công việc mới từ pool"""
        while self.running:
            try:
                response = self.receive_json()
                if response and response.get("method") == "mining.notify":
                    self.job = response["params"]
                    self.difficulty = self.difficulty or 1  # Sử dụng giá trị mặc định nếu pool không gửi độ khó
                    print(f"Nhận công việc mới: {self.job[0]}, Độ khó: {self.difficulty}")
                    self.extranonce1 = self.job[1]  # Extranonce1 lấy từ job
                    self.extranonce2_size = len(self.extranonce1) // 2  # Cập nhật kích thước extranonce2
            except Exception as e:
                print(f"Lỗi khi nhận công việc: {e}")
                self.running = False

    def mine(self):
        """Hàm khai thác thực tế"""
        thread_id = 0  # Cần truyền thread_id từ luồng
        while self.running:
            if not self.job:
                print("Chưa nhận được công việc từ pool. Đang chờ...")
                time.sleep(1)
                continue
            
            extranonce2 = f"{thread_id:0{self.extranonce2_size * 2}x}"  # Extranonce2 cho mỗi luồng
            coinbase = self.create_coinbase(extranonce2)  # Tạo coinbase cho công việc
            blockheader = self.create_blockheader(coinbase)  # Tạo blockheader
            nonce = self.mine_block(blockheader)  # Tính toán nonce hợp lệ
            if nonce:
                print(f"Đã tìm thấy nonce hợp lệ: {nonce}")
                self.submit_work(nonce)
                break  # Tạm dừng khi tìm thấy nonce hợp lệ
            time.sleep(1)  # Chờ 1 giây trước khi thử lại

    def create_coinbase(self, extranonce2):
        """Tạo coinbase từ extranonce1 và extranonce2"""
        coinb1 = b'\x01'  # Đoạn coinbase đầu tiên
        coinb2 = b'\x00'  # Đoạn coinbase thứ hai
        coinbase = coinb1 + self.extranonce1.encode('utf-8') + extranonce2.encode('utf-8') + coinb2
        return coinbase

    def create_blockheader(self, coinbase):
        """Tạo blockheader từ coinbase và các tham số khác"""
        prevhash = b'\x00' * 32  # Hash của block trước đó (giả sử)
        merkle_root = hashlib.sha256(coinbase).digest()  # Tính merkle root từ coinbase
        time_now = int(time.time())
        blockheader = prevhash + merkle_root + struct.pack("<I", time_now)  # Kết hợp các thông số
        return blockheader

    def mine_block(self, blockheader):
        """Tính toán nonce hợp lệ từ blockheader"""
        target = (2 ** (256 - self.difficulty)) - 1
        nonce = 0
        while nonce < 0xFFFFFFFF:
            block_with_nonce = blockheader + struct.pack("<I", nonce)
            blockhash = minotaurx_hash(block_with_nonce)  # Sử dụng hàm hash MinotaurX từ thư viện đã build
            if int.from_bytes(blockhash, 'little') < target:
                return nonce
            nonce += 1
        return None

    def submit_work(self, nonce):
        """Gửi kết quả khai thác về pool"""
        job_id = self.job[0]
        ntime = struct.pack("<I", int(time.time()))
        extranonce2 = f"{nonce:0{self.extranonce2_size * 2}x}"
        self.send_json({
            "id": 4,
            "method": "mining.submit",
            "params": [self.wallet, job_id, extranonce2, ntime, "00000000"]
        })
        print(f"Đã gửi kết quả khai thác với nonce: {nonce}")

if __name__ == '__main__':
    # Thông tin pool và wallet
    pool_url = "minotaurx.na.mine.zpool.ca"
    pool_port = 7019
    wallet = input("Nhập ví của bạn: ")
    
    miner = Miner(wallet, pool_url, pool_port)
    miner.handle_jobs()  # Nhận công việc từ pool
    miner.mine()  # Bắt đầu khai thác
