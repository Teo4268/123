import binascii as c
import hashlib as d
import struct as Q
import json
import time
import random as e
import websocket as ws
import threading
import logging

# Import thuật toán MinotaurX từ thư viện hoặc file đã biên dịch
try:
    from minotaurx_hash import getPoWHash  # Thư viện cung cấp hàm tính toán hash
except ImportError:
    raise ImportError("Thư viện minotaurx_hash chưa được cài đặt hoặc thiếu file. Vui lòng kiểm tra lại.")

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def endian_swap(hex_word):
    """Swap endianness of a 4-byte word."""
    binary = c.unhexlify(hex_word)
    if len(binary) != 4:
        raise ValueError("Input must be a 4-byte word")
    return binary[::-1]

def endian_swap_multi(hex_words):
    """Swap endianness of a multi-word hex string."""
    binary = c.unhexlify(hex_words)
    if len(binary) % 4 != 0:
        raise ValueError("Input must be 4-byte word aligned")
    return b"".join([binary[i:i+4][::-1] for i in range(0, len(binary), 4)])

def format_hashrate(hashrate):
    """Format hashrate for display."""
    if hashrate < 1_000:
        return f"{hashrate:.2f} H/s"
    elif hashrate < 1_000_000:
        return f"{hashrate / 1_000:.2f} kH/s"
    elif hashrate < 1_000_000_000:
        return f"{hashrate / 1_000_000:.2f} MH/s"
    else:
        return f"{hashrate / 1_000_000_000:.2f} GH/s"

class Job:
    def __init__(self, job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime, target, extranonce1, extranonce2_size):
        self.job_id = job_id
        self.prevhash = prevhash
        self.coinb1 = coinb1
        self.coinb2 = coinb2
        self.merkle_branches = merkle_branches
        self.version = version
        self.nbits = nbits
        self.ntime = ntime
        self.target = target
        self.extranonce1 = extranonce1
        self.extranonce2_size = extranonce2_size
        self.hash_count = 0
        self.start_time = time.time()

    def merkle_root(self, extranonce2):
        coinbase = (
            c.unhexlify(self.coinb1)
            + c.unhexlify(self.extranonce1)
            + extranonce2
            + c.unhexlify(self.coinb2)
        )
        merkle_root = d.sha256(d.sha256(coinbase).digest()).digest()
        for branch in self.merkle_branches:
            merkle_root = d.sha256(merkle_root + c.unhexlify(branch)).digest()
        return merkle_root

    def mine(self, nonce_start, nonce_end):
        extranonce2 = e.getrandbits(self.extranonce2_size * 8).to_bytes(self.extranonce2_size, 'little')
        merkle_root_bin = self.merkle_root(extranonce2)
        header = (
            endian_swap(self.version)
            + endian_swap_multi(self.prevhash)
            + merkle_root_bin
            + endian_swap(self.ntime)
            + endian_swap(self.nbits)
        )
        for nonce in range(nonce_start, nonce_end):
            nonce_bin = Q.pack("<I", nonce)
            hash_result = getPoWHash(header + nonce_bin)  # Sử dụng thuật toán MinotaurX
            if int(hash_result, 16) <= int(self.target, 16):
                yield {
                    "job_id": self.job_id,
                    "extranonce2": c.hexlify(extranonce2).decode(),
                    "ntime": self.ntime,
                    "nonce": f"{nonce:08x}",
                }
            self.hash_count += 1

    def hashrate(self):
        elapsed_time = time.time() - self.start_time
        return self.hash_count / elapsed_time if elapsed_time > 0 else 0

class Miner:
    def __init__(self, pool, port, username, password, threads=1):
        self.pool = pool
        self.port = port
        self.username = username
        self.password = password
        self.ws = None
        self.job = None
        self.extranonce1 = None
        self.extranonce2_size = None
        self.target = None
        self.threads = threads

    def connect(self):
        self.ws = ws.WebSocketApp(
            f"ws://{self.pool}:{self.port}",
            on_message=self.on_message,
            on_open=self.on_open,
            on_error=self.on_error,
        )
        threading.Thread(target=self.ws.run_forever).start()

    def on_open(self, ws):
        logging.info("Connected to pool")
        subscribe_message = {
            "id": 1,
            "method": "mining.subscribe",
            "params": [],
        }
        ws.send(json.dumps(subscribe_message))

    def on_message(self, ws, message):
        response = json.loads(message)
        method = response.get("method")
        params = response.get("params", [])

        if method == "mining.notify":
            self.handle_new_job(params)
        elif response.get("id") == 1:
            self.extranonce1, self.extranonce2_size = params[1], params[2]
            authorize_message = {
                "id": 2,
                "method": "mining.authorize",
                "params": [self.username, self.password],
            }
            ws.send(json.dumps(authorize_message))
        elif response.get("id") == 2:
            logging.info("Authorized successfully!")

    def on_error(self, ws, error):
        logging.error("Error: %s", error)

    def handle_new_job(self, params):
        logging.info("New job received")
        job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime, clean_jobs = params
        self.target = "00000000" + "f" * 56
        self.job = Job(
            job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime, self.target, self.extranonce1, self.extranonce2_size
        )
        threading.Thread(target=self.start_mining).start()

    def start_mining(self):
        if not self.job:
            logging.warning("No job available for mining")
            return
        logging.info("Mining started with %d threads...", self.threads)
        thread_list = []
        nonce_per_thread = 0xFFFFFFFF // self.threads
        for i in range(self.threads):
            start_nonce = i * nonce_per_thread
            end_nonce = start_nonce + nonce_per_thread
            thread = threading.Thread(target=self.mine_range, args=(start_nonce, end_nonce))
            thread_list.append(thread)
            thread.start()
        for thread in thread_list:
            thread.join()

    def mine_range(self, start_nonce, end_nonce):
        for result in self.job.mine(start_nonce, end_nonce):
            logging.info("Valid share found: %s", result)
            submit_message = {
                "id": 3,
                "method": "mining.submit",
                "params": [
                    self.username,
                    result["job_id"],
                    result["extranonce2"],
                    result["ntime"],
                    result["nonce"],
                ],
            }
            self.ws.send(json.dumps(submit_message))

if __name__ == "__main__":
    # Cấu hình mặc định
    pool = "minotaurx.sea.mine.zpool.ca"
    port = 7019
    username = "R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q"
    password = "c=RVN"
    
    threads = int(input("Enter number of threads: "))
    miner = Miner(pool, port, username, password, threads)
    miner.connect()
