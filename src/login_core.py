import socket
import re

class OpType:
    LOGIN = (0x00, 0x05)
    REGISTER = (0x02, 0x05)
    START_GAME = (0x06, 0x05)
    RECOVER = (0x04, 0x05)

def build_hex(op_code, *args):
    type_code, func_code = op_code

    if op_code == OpType.LOGIN:
        raw_str = f"{args[0]}/{args[1]}"
    elif op_code == OpType.REGISTER:
        raw_str = f"{args[0]}/{args[1]}/{args[2]}/{args[3]}/{args[3]}"
    elif op_code == OpType.RECOVER:
        raw_str = f"{args[0]}/{args[1]}/{args[2]}/{args[3]}"
    elif op_code == OpType.START_GAME:
        raw_str = f"{args[0]}:{args[1]}"
    else:
        raise ValueError(f"未处理的操作类型: {op_code}")

    raw_bytes = raw_str.encode('ascii')
    length = len(raw_bytes) + 4
    if length > 255:
        raise ValueError("Payload 太长！")

    return f"{type_code:02x}{func_code:02x}{length:02x}00" + raw_bytes.hex()

class GameClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect((self.server_ip, self.server_port))

    def send_and_receive(self, hex_data, expected_op=None):
        hex_data = ''.join(hex_data.split())
        if not re.fullmatch(r'[0-9a-fA-F]*', hex_data):
            return { "code": 500, "message": "非法十六进制数据" }

        try:
            data = bytes.fromhex(hex_data)
        except ValueError as e:
            print("十六进制转换失败:", e)
            return { "code": 500, "message": "转换失败" }

        try:
            self.socket.sendall(data)
            resp = self.socket.recv(1024)
        except Exception as e:
            print("网络通信失败:", e)
            return { "code": 500, "message": "网络通信失败" }

        return self.parse_response(resp, expected_op)

    def parse_response(self, resp, expected_op=None):
        if len(resp) < 2:
            return { "code": 500, "message": "响应数据太短，无法解析" }

        resp_type = resp[0]
        resp_func = resp[1]
        payload = resp[4:] if len(resp) > 4 else b''

        if expected_op is not None:
            type_code, func_code = expected_op
            if resp_type == type_code and resp_func == func_code:
                if expected_op == OpType.LOGIN:
                    try:
                        text = payload.decode('utf-8')
                        zones = []
                        for line in text.strip().split('\r\n'):
                            ip_port, name = line.split('/')
                            ip, port = ip_port.split(',')
                            zones.append({
                                "ip": ip,
                                "port": port,
                                "name": name
                            })
                        return { "code": 200, "data": zones }
                    except Exception as e:
                        print("区服解析失败:", e)
                        return { "code": 500, "message": "区服解析失败" }
                else:
                    try:
                        text = payload.decode('ascii')
                        return { "code": 200, "data": text }
                    except Exception as e:
                        print("ASCII 解码失败:", e)
                        return { "code": 200, "data": payload.hex() }
            else:
                try:
                    msg = payload.decode('utf-8')
                    return { "code": 500, "message": msg }
                except Exception as e:
                    print("错误信息解码失败:", e)
                    return { "code": 500, "message": "无法解码错误信息" }
        else:
            return { "code": 200, "data": resp.hex() }

    def close(self):
        self.socket.close()
