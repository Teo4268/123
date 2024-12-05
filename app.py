import socket
import json
import threading

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
