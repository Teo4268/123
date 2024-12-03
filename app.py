import socket
import json
import random
import struct
import threading
from multiprocessing import Process, Queue, Event
import minotaurx_hash  # Import thư viện MinotaurX để sử dụng PoW

class Miner:
    def __init__(self, host, port, username, password, threads=4):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.threads = threads
        self.socket = None
        self.job = None
        self.extranonce1 = None
        self.extranonce2_size = None
        self.target = None
        self.stop_event = Event()
        self.queue = Queue()
        self.processes = []

    def connect(self):
        """Kết nối trực tiếp tới pool qua TCP socket."""
        self.socket = socket.create_connection((self.host, self.port))
        self.socket.settimeout(5)
        print(f"Connected to pool {self.host}:{self.port}")

    def send_message(self, method, params):
        """Gửi thông điệp tới pool."""
        message = {
            "id": random.randint(1, 1000),
            "method": method,
            "params": params,
        }
        self.socket.sendall(json.dumps(message).encode("utf-8") + b"\n")

    def receive_message(self):
        """Nhận thông điệp từ pool."""
        buffer = b""
        while not buffer.endswith(b"\n"):
            buffer += self.socket.recv(1024)
        return json.loads(buffer.decode("utf-8").strip())

    def subscribe(self):
        """Đăng ký kết nối tới pool."""
        self.send_message("mining.subscribe", ["tcp_miner_minotaurx_pow"])
        response = self.receive_message()
        self.extranonce1, self.extranonce2_size = response["result"][1:3]
        print(f"Subscribed: extranonce1={self.extranonce1}, extranonce2_size={self.extranonce2_size}")

    def authorize(self):
        """Xác thực worker."""
        self.send_message("mining.authorize", [self.username, self.password])
        response = self.receive_message()
        if response["result"]:
            print("Authorized successfully!")
        else:
            print("Authorization failed!")

    def handle_job(self, params):
        """Nhận và xử lý công việc từ pool."""
        job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime, clean_jobs = params
        self.job = {
            "job_id": job_id,
            "prevhash": prevhash,
            "coinb1": coinb1,
            "coinb2": coinb2,
            "merkle_branches": merkle_branches,
            "version": version,
            "nbits": nbits,
            "ntime": ntime,
        }
        self.target = self.calculate_target(nbits)
        print(f"New job received: job_id={job_id}, target={self.target}")

    def calculate_target(self, nbits):
        """Tính toán target từ nbits."""
        packed = bytes.fromhex(nbits)
        exponent = packed[0]
        coefficient = int.from_bytes(packed[1:], byteorder="big")
        return coefficient * 2 ** (8 * (exponent - 3))

    def mine(self, job, extranonce2, nonce_start, nonce_end):
        """Thực hiện đào bằng hàm PoW của MinotaurX."""
        coinbase = job["coinb1"] + self.extranonce1 + extranonce2 + job["coinb2"]
        coinbase_hash = minotaurx_hash.get_hash(bytes.fromhex(coinbase))
        merkle_root = self.calculate_merkle_root(coinbase_hash.hex(), job["merkle_branches"])

        block_header = (
            job["version"] + job["prevhash"] + merkle_root + job["ntime"] + job["nbits"]
        )

        for nonce in range(nonce_start, nonce_end):
            if self.stop_event.is_set():
                return
            result = minotaurx_hash.pow(
                bytes.fromhex(block_header), nonce, self.target
            )  # Sử dụng hàm PoW
            if result:
                self.queue.put({
                    "id": job["job_id"],
                    "nonce": nonce,
                    "extranonce2": extranonce2,
                    "ntime": job["ntime"],
                })

    def calculate_merkle_root(self, coinbase_hash, merkle_branches):
        """Tính toán Merkle Root từ coinbase hash và các nhánh."""
        hash_result = coinbase_hash
        for branch in merkle_branches:
            hash_result = minotaurx_hash.get_hash(bytes.fromhex(hash_result + branch)).hex()
        return hash_result

    def submit_share(self, share):
        """Gửi share tới pool."""
        self.send_message("mining.submit", [
            self.username,
            share["id"],
            share["extranonce2"],
            share["ntime"],
            f"{share['nonce']:08x}"
        ])
        print(f"Share submitted: {share}")

    def listen(self):
        """Lắng nghe thông điệp từ pool."""
        while not self.stop_event.is_set():
            message = self.receive_message()
            method = message.get("method")
            params = message.get("params")
            if method == "mining.notify":
                self.handle_job(params)
            elif method == "mining.set_difficulty":
                pass  # Xử lý độ khó nếu cần

    def start_mining(self):
        """Bắt đầu quá trình đào."""
        self.connect()
        self.subscribe()
        self.authorize()

        listener_thread = threading.Thread(target=self.listen, daemon=True)
        listener_thread.start()

        while not self.stop_event.is_set():
            if self.job:
                processes = []
                for i in range(self.threads):
                    nonce_start = i * (2 ** 32 // self.threads)
                    nonce_end = (i + 1) * (2 ** 32 // self.threads)
                    extranonce2 = f"{random.randint(0, 2**32):08x}"
                    process = Process(
                        target=self.mine,
                        args=(self.job, extranonce2, nonce_start, nonce_end)
                    )
                    processes.append(process)
                    process.start()

                for process in processes:
                    process.join()

                while not self.queue.empty():
                    share = self.queue.get()
                    self.submit_share(share)


if __name__ == "__main__":
    host = "minotaurx.na.mine.zpool.ca"
    port = 7019
    username = "R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q"
    password = "c=RVN"
    threads = 3

    miner = Miner(host, port, username, password, threads)
    try:
        miner.start_mining()
    except KeyboardInterrupt:
        miner.stop_event.set()
        print("Stopping miner...")
