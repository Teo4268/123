import websocket
import json
import struct
import random
import time
import threading
import multiprocessing
import binascii
import queue
import minotaurx_hash

# Các hàm hỗ trợ MinotaurX hash
def minotaurx_proof_of_work(header):
    return minotaurx_hash.hash(header)  # Sử dụng MinotaurX để băm

def format_hashrate(hashrate):
    if hashrate < 1000:
        return f'{hashrate} B/s'
    elif hashrate < 1000000:
        return f'{hashrate / 1000} KB/s'
    elif hashrate < 1000000000:
        return f'{hashrate / 1000000} MB/s'
    else:
        return f'{hashrate / 1000000000} GB/s'

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
        self.done = False
        self.dt = 0
        self.hash_count = 0

    def hashrate(self):
        if self.dt == 0:
            return 0
        return self.hash_count / self.dt

    def mine(self, nonce_start=0, nonce_end=1):
        start_time = time.time()
        extranonce2 = '{:0{width}x}'.format(random.randint(0, 2**(8*self.extranonce2_size)-1), self.extranonce2_size * 2)
        extranonce2_bin = struct.pack('<I', int(extranonce2, 16)) if self.extranonce2_size <= 4 else struct.pack('<Q', int(extranonce2, 16))
        merkle_root = self.merkle_root_bin(extranonce2_bin)
        header = self.version + self.prevhash + merkle_root + self.ntime + self.nbits
        for nonce in range(nonce_start, nonce_end):
            if self.done:
                self.dt += time.time() - start_time
                raise StopIteration()
            packed_nonce = struct.pack('<I', nonce)
            pow_hash = binascii.hexlify(self.proof_of_work(header + packed_nonce)[::-1]).decode('utf-8')
            if int(pow_hash, 16) <= int(self.target, 16):
                self.dt += time.time() - start_time
                yield {'job_id': self.job_id, 'extranonce2': binascii.hexlify(extranonce2_bin), 'ntime': self.ntime, 'nonce': binascii.hexlify(packed_nonce[::-1])}
            self.hash_count += 1
        self.dt += time.time() - start_time

    def merkle_root_bin(self, extranonce2_bin):
        coinbase = binascii.unhexlify(self.coinb1) + binascii.unhexlify(self.extranonce1) + extranonce2_bin + binascii.unhexlify(self.coinb2)
        hash_result = minotaurx_proof_of_work(coinbase)  # Sử dụng MinotaurX để băm
        for branch in self.merkle_branches:
            hash_result = minotaurx_proof_of_work(hash_result + binascii.unhexlify(branch))  # Sử dụng MinotaurX để băm
        return hash_result

class Subscription:
    def __init__(self, pool_host, pool_port, username, password):
        self.pool_host = pool_host
        self.pool_port = pool_port
        self.username = username
        self.password = password
        self.worker_name = None
        self.target = None
        self.job = None

    def set_worker_name(self, worker_name):
        self.worker_name = worker_name

    def set_target(self, target):
        self.target = target

    def create_job(self, job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime):
        return Job(job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime, self.target, self.username, 4)

    def proof_of_work(self, header):
        return minotaurx_proof_of_work(header)  # Sử dụng MinotaurX để băm

class Miner:
    def __init__(self, pool_host, pool_port, username, password, threads=4, retries=5):
        self.pool_host = pool_host
        self.pool_port = pool_port
        self.username = username
        self.password = password
        self.threads = threads
        self.retries = retries
        self.subscription = Subscription(pool_host, pool_port, username, password)
        self.jobs = []
        self.queue = queue.Queue()

    def on_message(self, ws, message):
        try:
            msg = json.loads(message)
            if msg.get('method') == 'mining.notify':
                job_data = msg.get('params')
                job = self.subscription.create_job(*job_data)
                self.jobs.append(job)
                self.start_mining(job)
        except Exception as e:
            print(f"Error in on_message: {e}")

    def start_mining(self, job):
        nonce_range = self.calculate_nonce_range()
        process = multiprocessing.Process(target=self.run_mining, args=(job, nonce_range))
        process.start()

    def run_mining(self, job, nonce_range):
        for result in job.mine(*nonce_range):
            self.queue.put(result)

    def calculate_nonce_range(self):
        total_range = 100000
        return (0, total_range // self.threads)

    def on_open(self, ws):
        ws.send(json.dumps({"method": "mining.subscribe", "params": []}))

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("Connection closed")
        # Tự động kết nối lại nếu bị mất kết nối
        for _ in range(self.retries):
            print("Retrying to connect...")
            time.sleep(5)
            self.connect()

    def connect(self):
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(f"ws://{self.pool_host}:{self.pool_port}",
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
        ws.on_open = self.on_open
        ws.run_forever()

if __name__ == '__main__':
    miner = Miner(pool_host='minotaurx.na.mine.zpool.ca', pool_port=7019, username='R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q', password='c=RVN', threads=4, retries=5)
    miner.connect()
