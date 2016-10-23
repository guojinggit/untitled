import socket
import threadpool
import random
import time

def server_login(str_p):
    # 该层while保证线程不死，并且每次都会创建一个新的sock（因为上一个sock已经死掉了）
    while True:
        host, port = "103.55.27.154", 9999
        #host, port = "localhost", 9999
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        data_send = "server_login"
        sock.send(bytes(data_send, "utf_8"))
        print('已经发送注册请求数据')

        # 只要sock不死，就保持常连接
        while True:
            data_received = sock.recv(1024*1024)
            data_length = len(data_received)
            # sock已经死掉，退出该while
            if data_length == 0:
                break
            if data_length > 6 and data_received[0] == ord('l') and data_received[6] == ord('t'):
                print("注册成功")
            str_array = data_received.split(b"+", 3)
            # 来自中转站的消息,将此消息转给tomcat服务器
            if str(str_array[0], "utf_8") == "to_server":
                print(str(str_array[3], "utf_8"))
                # 提取key，之后作为协议头转发给中转站
                key = "{}+{}".format(str(str_array[1], "utf_8"), str(str_array[2], "utf_8"))
                sock_to_tomcat = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock_to_tomcat.connect(("localhost", 8080))
                sock_to_tomcat.send(str_array[3])  # 将消息发送到tomcat
                # 一直接收来自tomcat的数据，直到tomcat发送完毕，关闭sock为止（防止数据接收不完整）
                time1 = time.time()
                last_length = 0
                while True:
                    received_from_tomcat = sock_to_tomcat.recv(9000)
                    current_length = len(received_from_tomcat)
                    print(current_length)
                    if current_length == 0:
                        break
                    sock.send(bytes("to_client+{}+".format(key), "utf_8") + received_from_tomcat)
                    if current_length < last_length:
                        break
                    if current_length < 9000:
                        break
                    last_length = current_length
                    print("已经回包")
                time2 = time.time()
                print("tomcat请求间隔：" + str(time2 - time1))
        # 防止一直重连消耗cpu
        time.sleep(5)

# 函数必须带参数，每个函数的参数可以不一样，10个线程对应10个参数
argList = [random.randint(1, 10) for i in range(10)]
pool = threadpool.ThreadPool(2)
# server_login不需要参数，所以给了10个没有意义的参数
requests = threadpool.makeRequests(server_login, argList)
[pool.putRequest(req) for req in requests]
pool.wait()

