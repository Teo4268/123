import socket
import json
import threading

class Miner:
    def __init__(self, pool_url, wallet, port, password, threads):
        self.pool_url = pool_url
        self.wallet = wallet
        self.port = port
        self.password = password
        self.threads = threads
        self.connection = None
        self.job = None
        self.extranonce1 = None
        self.extranonce2_size = None
        self.running = True

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
        self.connection.sendall((json.dumps(data) + "\n").encode())

    def receive_json(self):
        """Nhận dữ liệu JSON từ pool."""
        try:
            response = self.connection.recv(4096).decode()
            for line in response.splitlines():
                return json.loads(line)
        except Exception as e:
            print(f"Lỗi khi nhận dữ liệu: {e}")
            return None

    def handle_jobs(self):
        """Nhận công việc mới từ pool."""
        while self.running:
            try:
                response = self.receive_json()
                print("Phản hồi nhận được:", response)  # In ra để kiểm tra dữ liệu trả về
                if response and response.get("method") == "mining.notify":
                    self.job = response["params"]
                    if self.job:
                        print(f"Nhận công việc mới: {self.job[0]}")
                    else:
                        print("Công việc không hợp lệ.")
                        self.running = False
                else:
                    print(f"Phản hồi không hợp lệ hoặc không phải 'mining.notify': {response}")
            except Exception as e:
                print(f"Lỗi khi nhận công việc: {e}")
                self.running = False

    def mine(self, thread_id):
        """Giả lập khai thác mà không tính toán."""
        while self.running:
            if self.job:
                print(f"[Thread {thread_id}] Đang khai thác công việc {self.job[0]}")
            else:
                print(f"[Thread {thread_id}] Chưa có công việc.")
            # Giả lập dừng lại sau một thời gian
            import time
            time.sleep(2)

    def start(self):
        """Bắt đầu đào coin."""
        self.connect()
        if self.running:
            self.subscribe()
        if self.running:
            self.authorize()

        if self.running:
            # Chạy luồng nhận công việc
            threading.Thread(target=self.handle_jobs, daemon=True).start()

            # Tạo các luồng khai thác giả lập
            threads = []
            for i in range(self.threads):
                thread = threading.Thread(target=self.mine, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

if __name__ == "__main__":
    pool = "minotaurx.na.mine.zpool.ca"  # Địa chỉ pool
    wallet = "R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q"  # Ví của bạn
    port = 7019  # Port của pool
    password = "c=RVN"  # Password
    threads = 2  # Số luồng

    miner = Miner(pool, wallet, port, password, threads)
    miner.start()
