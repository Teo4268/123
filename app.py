import socket
import json
import random
import time
import struct
import threading
import minotaurx_hash as x

# Các hằng số cần thiết
o = 'hashrate'
n = 'shared'
m = '%064x'
l = False
k = 'port'
j = 'minotaurx'
i = tuple
h = ValueError
b = 'hashrate'
a = 'mining.submit'
Z = 'threads'
Y = print
X = range
W = isinstance
P = True
O = Exception
M = len
J = '\n'
H = 'params'
G = 'method'
F = 'id'
D = int
B = None
A = property

# Lớp v (Subscription)
class v:
    _max_nonce = 4294967295

    def ProofOfWork(A):
        raise O('Do not use the Subscription class directly, subclass it')

    class StateException(O): pass
    
    def __init__(A):
        A._id = B
        A._difficulty = B
        A._extranonce1 = B
        A._extranonce2_size = B
        A._target = B
        A._worker_name = B
        A._mining_thread = B

    id = A(lambda s: s._id)
    worker_name = A(lambda s: s._worker_name)
    difficulty = A(lambda s: s._difficulty)
    target = A(lambda s: s._target)
    extranonce1 = A(lambda s: s._extranonce1)
    extranonce2_size = A(lambda s: s._extranonce2_size)

    def set_worker_name(A, worker_name):
        if A._worker_name:
            raise A.StateException(f'Already authenticated as {A._worker_name} (requesting {worker_name})')
        A._worker_name = worker_name

    def _set_target(A, target):
        A._target = m % target

    def set_difficulty(B, difficulty):
        A = difficulty
        if A < 0:
            raise B.StateException('Difficulty must be non-negative')
        if A == 0:
            C = 2**256 - 1
        else:
            C = min(D((4294901760 * 2**(256-64) + 1) / A - 1 + .5), 2**256 - 1)
        B._difficulty = A
        B._set_target(C)

    def set_subscription(A, subscription_id, extranonce1, extranonce2_size):
        if A._id is not B:
            raise A.StateException('Already subscribed')
        A._id = subscription_id
        A._extranonce1 = extranonce1
        A._extranonce2_size = extranonce2_size

    def create_job(A, job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime):
        if A._id is B:
            raise A.StateException('Not subscribed')
        return u(job_id=job_id, prevhash=prevhash, coinb1=coinb1, coinb2=coinb2, merkle_branches=merkle_branches, version=version, nbits=nbits, ntime=ntime, target=A.target, extranonce1=A._extranonce1, extranonce2_size=A._extranonce2_size, proof_of_work=A.ProofOfWork, max_nonce=A._max_nonce)

    def __str__(A):
        return f'<Subscription id={A.id}, extranonce1={A.extranonce1}, extranonce2_size={A.extranonce2_size}, difficulty={A.difficulty} worker_name={A.worker_name}>'

# Lớp u (Job)
class u:
    def __init__(A, job_id, prevhash, coinb1, coinb2, merkle_branches, version, nbits, ntime, target, extranonce1, extranonce2_size, proof_of_work, max_nonce=4294967295):
        A._job_id = job_id
        A._prevhash = prevhash
        A._coinb1 = coinb1
        A._coinb2 = coinb2
        A._merkle_branches = [A for A in merkle_branches]
        A._version = version
        A._nbits = nbits
        A._ntime = ntime
        A._max_nonce = max_nonce
        A._target = target
        A._extranonce1 = extranonce1
        A._extranonce2_size = extranonce2_size
        A._proof_of_work = proof_of_work
        A._done = l
        A._dt = .0
        A._hash_count = 0

    id = A(lambda s: s._job_id)
    prevhash = A(lambda s: s._prevhash)
    coinb1 = A(lambda s: s._coinb1)
    coinb2 = A(lambda s: s._coinb2)
    merkle_branches = A(lambda s: [A for A in s._merkle_branches])
    version = A(lambda s: s._version)
    nbits = A(lambda s: s._nbits)
    ntime = A(lambda s: s._ntime)
    target = A(lambda s: s._target)
    extranonce1 = A(lambda s: s._extranonce1)
    extranonce2_size = A(lambda s: s._extranonce2_size)
    proof_of_work = A(lambda s: s._proof_of_work)

    @A
    def hashrate(self):
        A = self
        if A._dt == 0:
            return .0
        return A._hash_count / A._dt

    def merkle_root_bin(A, extranonce2_bin):
        C = I(A._coinb1) + I(A._extranonce1) + extranonce2_bin + I(A._coinb2)
        D = g(C)
        B = D
        for E in A._merkle_branches:
            B = g(B + I(E))
        return B

    def stop(A):
        A._done = P

    def mine(A, nonce_start=0, nonce_end=1):
        B = K.time()
        C = '{:0{}x}'.format(random.randint(0, 2**(8 * A.extranonce2_size) - 1), A.extranonce2_size * 2)
        E = struct.pack('<I', D(C, 16)) if A.extranonce2_size <= 4 else struct.pack('<Q', D(C, 16))
        G = A.merkle_root_bin(E)
        H = V(A._version) + s(A._prevhash) + G + V(A._ntime) + V(A._nbits)
        I = X(nonce_start, nonce_end, 1)
        for J in I:
            if A._done:
                A._dt += K.time() - B
                raise StopIteration()
            F = struct.pack('<I', J)
            pow = U(A.proof_of_work(H + F)[::-1]).decode('utf-8')
            if D(pow, 16) <= D(A.target, 16):
                L = dict(job_id=A.id, extranonce2=U(E), ntime=str(A._ntime), nonce=U(F[::-1]))
                A._dt += K.time() - B
                yield L
            B = K.time()
            A._hash_count += 1

    def __str__(A):
        return f'<Job id={A.id} prevhash={A.prevhash} coinb1={A.coinb1} coinb2={A.coinb2} merkle_branches={A.merkle_branches} version={A.version} nbits={A.nbits} ntime={A.ntime} target={A.target} extranonce1={A.extranonce1} extranonce2_size={A.extranonce2_size}>'

# Lớp w (Kế thừa từ v)
class w(v):
    ProofOfWork = x.getPoWHash
    _max_nonce = 4294967295

    def _set_target(A, target):
        A._target = m % target

# Miner class
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
        self.target = None  # Khởi tạo target là None
        self.difficulty = None  # Khởi tạo độ khó là None
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
            # Chuyển đổi độ khó từ chuỗi hex thành số nguyên
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
        """Nhận công việc mới từ pool."""
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
                    else:
                        print("Công việc không hợp lệ.")
                        self.running = False
                else:
                    print(f"Phản hồi không hợp lệ hoặc không phải 'mining.notify': {response}")
            except Exception as e:
                print(f"Lỗi khi nhận công việc: {e}")
                self.running = False

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
