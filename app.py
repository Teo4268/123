import socket
import time
import struct
import threading
import argparse
from minotaurx_hash import minotaurx_hash  # Import your hashing library here

# Function to connect to the pool and send data
def connect_to_pool(pool_url, wallet, password):
    host, port = pool_url.split(":")
    port = int(port)
    
    # Connect to the stratum pool
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    
    # Stratum handshake (init)
    request = {
        "id": 1,
        "method": "mining.subscribe",
        "params": []
    }
    s.sendall(bytes(f"{str(request)}\n", "utf-8"))
    
    # Wait for subscription response
    response = s.recv(1024)
    print(f"Received subscription response: {response}")
    
    # Subscribe worker
    request = {
        "id": 2,
        "method": "mining.authorize",
        "params": [wallet, password]
    }
    s.sendall(bytes(f"{str(request)}\n", "utf-8"))
    
    return s

# Function to mine using multiple threads
def mine_thread(pool_url, wallet, password, keepalive, threads):
    # Establish connection with the pool
    s = connect_to_pool(pool_url, wallet, password)
    
    # Work for each thread
    def mine_worker(thread_id):
        while True:
            # Receive mining job from the pool (work)
            data = s.recv(1024)
            print(f"Thread {thread_id} received work: {data}")
            
            # Perform hashing task (mining)
            job_data = struct.unpack("<80s", data)
            result = minotaurx_hash(job_data)
            
            # Send the result back to the pool
            response = {
                "id": thread_id,
                "method": "mining.submit",
                "params": [wallet, "job_id", result]
            }
            s.sendall(bytes(f"{str(response)}\n", "utf-8"))
            print(f"Thread {thread_id} sent result: {result}")
            
            if keepalive:
                # Send keepalive message every 60 seconds
                keepalive_message = {
                    "id": thread_id,
                    "method": "mining.keepalive",
                    "params": []
                }
                s.sendall(bytes(f"{str(keepalive_message)}\n", "utf-8"))
                print(f"Thread {thread_id} sent keepalive")
                
            time.sleep(2)  # Simulate mining work speed
    
    # Start threads
    threads_list = []
    for i in range(threads):
        thread = threading.Thread(target=mine_worker, args=(i,))
        threads_list.append(thread)
        thread.start()

    for thread in threads_list:
        thread.join()

# Main function to parse arguments and start mining
def main():
    parser = argparse.ArgumentParser(description="MinotaurX Coin Miner")
    parser.add_argument("--algorithm", type=str, default="minotaurx", help="Mining algorithm")
    parser.add_argument("--pool", type=str, required=True, help="Pool URL (e.g., minotaurx.sea.mine.zpool.ca:7019)")
    parser.add_argument("--wallet", type=str, required=True, help="Your wallet address")
    parser.add_argument("--password", type=str, default="c=RVN", help="Password (e.g., c=RVN)")
    parser.add_argument("--keepalive", type=bool, default=True, help="Enable keepalive (true/false)")
    parser.add_argument("--threads", type=int, default=1, help="Number of threads to use")
    
    args = parser.parse_args()
    
    print(f"Mining with algorithm: {args.algorithm}")
    print(f"Pool: {args.pool}")
    print(f"Wallet: {args.wallet}")
    print(f"Password: {args.password}")
    
    # Start mining
    mine_thread(args.pool, args.wallet, args.password, args.keepalive, args.threads)

if __name__ == "__main__":
    main()
