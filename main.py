import socketserver
import threading
import time

SOCK_MAP_ADDRESS_SERVER = {}
SOCK_MAP_ADDRESS_SERVER_STATUS = {}
SOCK_MAP_ADDRESS_CLIENT = {}
SOCK_MAP_ADDRESS_CLIENT_STATUS = {}

def is_from_server(ip, port):
    info = "{}+{}".format(ip, port)
    for key in SOCK_MAP_ADDRESS_SERVER.keys():
        if info == key:
            return True
    return False

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # 无论如何，本线程要么是和服务器保持长连接，要么和客户端保持长连接,只会是其中之一
        shutdown_flag = False
        while not shutdown_flag:
            data = self.request.recv(1024*4)
            key = "{}+{}".format(self.client_address[0], self.client_address[1])
            data_length = len(data)
            print("接收到的消息长度" , data_length)
            if data_length == 0:
                # 保持长连接的sock死掉了，那就得把字典里面的内容删掉了
                if is_from_server(self.client_address[0], self.client_address[1]):  # 删掉服务器的sock
                    global SOCK_MAP_ADDRESS_SERVER
                    SOCK_MAP_ADDRESS_SERVER.pop(key)
                else:
                    global SOCK_MAP_ADDRESS_CLIENT
                    if key in SOCK_MAP_ADDRESS_CLIENT.keys():
                        SOCK_MAP_ADDRESS_CLIENT.pop(key)
                break

            print("消息来了")
            # 先判断是否是服务器的注册消息，因为最开始并不知道哪个才是服务器的消息
            if data_length > 7 and data[0] == ord('s') and data[7] == ord('l'):  # 服务器注册自己的信息
                SOCK_MAP_ADDRESS_SERVER[key] = self.request  # 将服务器已建立连接sock插入字典
                SOCK_MAP_ADDRESS_SERVER_STATUS[key] = "free"  # 初始状态空闲
                self.request.send(bytes("login true", "utf_8"))
            else:  # 消息
                if is_from_server(self.client_address[0], self.client_address[1]):  # 来自服务器的消息
                    print("来自服务器的消息")
                    byte_array = data.split(b"+", 4)
                    should_length = int(byte_array[3])
                    data_length -= (len(byte_array[0] + byte_array[1] + byte_array[2] + byte_array[3]) + 4)
                    print(should_length, data_length)
                    if should_length > data_length:
                        while True:
                            data_others = self.request.recv(1024 * 10)
                            print("循环接收长度：",len(data_others))
                            data += data_others
                            data_length += len(data_others)
                            if data_length == should_length:
                                print("数据完整")
                                break
                            if data_length > should_length:
                                print("粘包")
                                break
                    byte_array = data.split(b"+", 4)
                    key_client_from_server = "{}+{}".format(str(byte_array[1], "utf_8"), str(byte_array[2], "utf_8"))
                    if key_client_from_server in SOCK_MAP_ADDRESS_CLIENT:
                        sock = SOCK_MAP_ADDRESS_CLIENT[key_client_from_server]
                        # 循环发送
                        send_total_length = 0
                        while True:
                            send_length = sock.send(byte_array[4][send_total_length:])  # 将消息发送到客户端
                            print(send_length)
                            if send_total_length == should_length or send_length == 0:
                                break
                            send_total_length += send_length

                        SOCK_MAP_ADDRESS_CLIENT_STATUS[key_client_from_server] = "false"

                    else:
                        print("客户端的sock已经断开连接了")

                else:   # 来自客户端消息
                    print("来自客户端的消息")
                    print((data, "utf_8"))
                    SOCK_MAP_ADDRESS_CLIENT[key] = self.request  # 将客户端已经建立连接的sock插入字典
                    SOCK_MAP_ADDRESS_CLIENT_STATUS[key] = "true"
                    to_server_data = "to_server+{}+".format(key)
                    # 来自客户端的消息，需要转发给服务器，这里从字典选个空闲的sock
                    is_not_send = True
                    while is_not_send:
                        for key_server in SOCK_MAP_ADDRESS_SERVER.keys():
                            if SOCK_MAP_ADDRESS_SERVER_STATUS[key_server] == "free":  # 如果sock空闲
                                SOCK_MAP_ADDRESS_SERVER_STATUS[key_server] = "busy"  # 将要发送，忙
                                SOCK_MAP_ADDRESS_SERVER[key_server].send(bytes(to_server_data, "utf_8") + data)
                                print("打印服务器的key:" + key_server)
                                is_not_send = False
                                SOCK_MAP_ADDRESS_SERVER_STATUS[key_server] = "free"  # 发送完了，空闲
                                break
                    time_total = 0
                    while True:
                        if SOCK_MAP_ADDRESS_CLIENT_STATUS[key] == "false" or time_total > 10:
                            shutdown_flag = True
                            break
                        time.sleep(0.1)
                        time_total += 0.1

if __name__ == "__main__":
    #HOST, PORT = "localhost", 9999
    HOST, PORT = "103.55.27.154", 9999
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()
    server_thread.join()
