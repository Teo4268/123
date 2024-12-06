import socket
import time
import logging
import minotaurx_hash  # Thư viện của bạn đã build

# Cấu hình logging để ghi log ra terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Thông tin pool và ví
POOL_HOST = 'minotaurx.na.mine.zpool.ca'
POOL_PORT = 7019
WALLET_ADDRESS = 'R9uHDn9XXqPAe2TLsEmVoNrokmWsHREV2Q'
WORKER_NAME = 'worker1'  # Bạn có thể thay đổi tên worker nếu cần
PASSWORD = 'c=RVN'

# Độ khó (difficulty) mà bạn sẽ kiểm tra trong PoW
DIFFICULTY = 0x0000ffffffffffffffffffffffffffffffffffffffffffffffffffffffff

# Tạo socket kết nối tới pool
def connect_to_pool():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((POOL_HOST, POOL_PORT))
        logging.info(f"Đã kết nối tới pool {POOL_HOST}:{POOL_PORT}")
        return sock
    except Exception as e:
        logging.error(f"Lỗi khi kết nối tới pool: {e}")
        return None

# Gửi dữ liệu tới pool
def send_to_pool(sock, data):
    try:
        sock.sendall(data.encode('utf-8'))
        logging.info(f"Đã gửi dữ liệu tới pool: {data}")
    except Exception as e:
        logging.error(f"Lỗi khi gửi dữ liệu tới pool: {e}")

# Hàm kiểm tra Proof of Work (PoW)
def check_pow(header, difficulty):
    # Tính toán hash bằng minotaurx_hash
    hash_result = minotaurx_hash.minotaurx_hash(header)
    # Kiểm tra nếu hash nhỏ hơn độ khó
    return int(hash_result, 16) < difficulty

# Đào coin và tính toán với MinotaurX
def mine_coin():
    sock = connect_to_pool()
    if not sock:
        return

    # Xác thực với pool
    auth_message = '{"id": 1, "method": "mining.subscribe", "params": []}\n'
    send_to_pool(sock, auth_message)

    # Gửi thông tin xác thực worker
    worker_message = f'{{"id": 1, "method": "mining.authorize", "params": ["{WALLET_ADDRESS}.{WORKER_NAME}", "{PASSWORD}"]}}\n'
    send_to_pool(sock, worker_message)

    # Lệnh đào với thuật toán MinotaurX (ở đây bạn cần thay dữ liệu này với yêu cầu của pool cụ thể)
    while True:
        try:
            data_from_pool = sock.recv(1024).decode('utf-8')
            if not data_from_pool:
                break

            logging.info(f"Nhận dữ liệu từ pool: {data_from_pool}")

            # Giả sử pool gửi công việc dưới dạng job_data, bạn cần xử lý dữ liệu này và hash
            # Các trường job_id, block_header, nonce và difficulty sẽ có trong dữ liệu pool gửi
            # Giả sử `data_from_pool` chứa thông tin job

            # Tiến hành hash với minotaurx_hash
            hash_result = minotaurx_hash.minotaurx_hash(data_from_pool.encode('utf-8'))  # Sử dụng hàm hash từ thư viện của bạn

            # Kiểm tra Proof of Work (PoW) với độ khó
            if check_pow(data_from_pool.encode('utf-8'), DIFFICULTY):
                # Gửi kết quả hash về pool
                result_message = f'{{"id": 1, "method": "mining.submit", "params": ["{WORKER_NAME}", "{data_from_pool}", "{hash_result}"]}}\n'
                send_to_pool(sock, result_message)

            time.sleep(1)  # Lặp lại sau 1 giây hoặc điều chỉnh theo nhu cầu

        except Exception as e:
            logging.error(f"Lỗi trong quá trình đào: {e}")
            break

if __name__ == "__main__":
    mine_coin()
