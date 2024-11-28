import json
import time
import random
import struct
import threading
import multiprocessing
from websocket import WebSocketApp
from hashlib import sha256
from minotaurx_hash import getPoWHash  # Thư viện đã biên sẵn

def sha256d(data):
    return sha256(sha256(data).digest()).digest()

def format_hashrate(hashrate):
    if hashrate < 1000:
        return f"{hashrate:.2f} H/s"
    elif hashrate < 1_000_000:
        return f"{hashrate / 1_000:.2f} kH/s"
    elif hashrate < 1_000_000_000:
        return f"{hashrate / 1_000_000:.2f} MH/s"
    else:
        return f"{hashrate / 1_000_000_000:.2f} GH/s"

class Miner:
    def __init__(self, pool_url, wallet, password, algorithm="minotaurx", threads=4):
        self.pool_url = pool_url
        self.wallet = wallet
        self.password = password
        self.algorithm = algorithm
        self.threads = threads
        self.jobs = []
        self.stop_event = multiprocessing.Event()
        self.hashrates = multiprocessing.Queue()
        self.accepted_shares = multiprocessing.Value('i', 0)

    def start(self):
        self.ws = WebSocketApp(
            self.pool_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()

    def on_open(self, ws):
        print("Connected to the pool.")
        subscribe_message = {
            "id": 1,
            "method": "mining.subscribe",
            "params": [],
        }
        ws.send(json.dumps(subscribe_message))

    def on_message(self, ws, message):
        response = json.loads(message)
        if "result" in response:
            if response["id"] == 1:  # Subscription response
                print("Subscribed successfully.")
                self.extranonce1 = response["result"][1]
                self.extranonce2_size = response["result"][2]
                authorize_message = {
                    "id": 2,
                    "method": "mining.authorize",
                    "params": [self.wallet, self.password],
                }
                ws.send(json.dumps(authorize_message))
        elif "method" in response and response["method"] == "mining.notify":
            params = response["params"]
            job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime, clean_jobs = params
            self.jobs = []
            for i in range(self.threads):
                start_nonce = i * (2**32 // self.threads)
                end_nonce = (i + 1) * (2**32 // self.threads)
                process = multiprocessing.Process(
                    target=self.mine_job,
                    args=(
                        job_id,
                        prevhash,
                        coinb1,
                        coinb2,
                        merkle_branches,
                        version,
                        nbits,
                        ntime,
                        start_nonce,
                        end_nonce,
                    ),
                )
                process.start()
                self.jobs.append(process)

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("Disconnected from the pool.")
        self.stop_event.set()

    def mine_job(self, job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime, start_nonce, end_nonce):
        target = int(nbits, 16)
        coinbase_bin = (
            bytes.fromhex(coinb1)
            + bytes.fromhex(self.extranonce1)
            + struct.pack("<I", random.randint(0, 2**32 - 1))
            + bytes.fromhex(coinb2)
        )
        coinbase_hash = sha256d(coinbase_bin)
        merkle_root = coinbase_hash
        for branch in merkle_branches:
            merkle_root = sha256d(merkle_root + bytes.fromhex(branch))
        block_header = (
            bytes.fromhex(version)
            + bytes.fromhex(prevhash)[::-1]
            + merkle_root
            + bytes.fromhex(ntime)[::-1]
            + bytes.fromhex(nbits)[::-1]
        )
        for nonce in range(start_nonce, end_nonce):
            if self.stop_event.is_set():
                return
            nonce_bin = struct.pack("<I", nonce)
            block = block_header + nonce_bin
            hash_bin = getPoWHash(block)
            hash_int = int.from_bytes(hash_bin[::-1], byteorder="big")
            if hash_int < target:
                share_message = {
                    "id": 4,
                    "method": "mining.submit",
                    "params": [self.wallet, job_id, struct.pack("<I", nonce).hex()],
                }
                self.ws.send(json.dumps(share_message))
                with self.accepted_shares.get_lock():
                    self.accepted_shares.value += 1

if __name__ == "__main__":
    pool_url = "ws://minotaurx.sea.mine.zpool.ca:7019"
    wallet = "R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q"
    password = "c=RVN"
    miner = Miner(pool_url, wallet, password, threads=2)
    miner.start()
