import socket
import re

class OpType:
    LOGIN = (0x00, 0x05)
    REGISTER = (0x02, 0x05)
    START_GAME = (0x06, 0x05)
    RECOVER = (0x04, 0x05)

    @classmethod
    def name_map(cls):
        return {
            cls.LOGIN: "login",
            cls.REGISTER: "register",
            cls.START_GAME: "start_game",
            cls.RECOVER: "recover"
        }

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

def send_and_receive(s, hex_data, expected_op=None):
    hex_data = ''.join(hex_data.split())
    if not re.fullmatch(r'[0-9a-fA-F]*', hex_data):
        return { "code": 500, "message": "非法十六进制数据" }
    
    try:
        data = bytes.fromhex(hex_data)
    except ValueError as e:
        return { "code": 500, "message": f"转换失败: {e}" }
    
    s.sendall(data)
    print(f"✅ 已发送: {hex_data}")
    resp = s.recv(1024)
    print(f"✅ 收到回应: {resp.hex()} {resp}")
    
    return parse_response(resp, expected_op)

def parse_response(resp, expected_op=None):
    if len(resp) < 2:
        return { "code": 500, "message": "响应数据太短，无法解析" }
    
    resp_type = resp[0]
    resp_func = resp[1]
    payload = resp[4:] if len(resp) > 4 else b''
    
    if expected_op is not None:
        type_code, func_code = expected_op
        if resp_type == type_code and resp_func == func_code:
            if expected_op == OpType.LOGIN:
                # 登录成功，解析区服列表
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
                    return { "code": 500, "message": f"区服解析失败: {e}" }
            else:
                try:
                    text = payload.decode('ascii')
                    return { "code": 200, "data": text }
                except:
                    return { "code": 200, "data": payload.hex() }
        else:
            try:
                msg = payload.decode('utf-8')
                return { "code": 500, "message": msg }
            except:
                return { "code": 500, "message": f"无法解码错误信息: {payload.hex()}" }
    else:
        return { "code": 200, "data": resp.hex() }

def main():
    ip = "192.168.1.3"
    port = 8001
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, port))
        print(f"✅ 已连接 {ip}:{port}")

        # 登录
        login_hex = build_hex(OpType.LOGIN, "yuxiang114", "123321")
        result = send_and_receive(s, login_hex, OpType.LOGIN)
        if result["code"] != 200:
            print(f"❌ 登录失败: {result['message']}")
            return
        zones = result["data"]
        print(f"🎉 登录成功，区服信息:")
        for z in zones:
            print(f"  - {z['ip']}:{z['port']} / {z['name']}")

        # 启动游戏
        zone = zones[0]
        game_hex = build_hex(OpType.START_GAME, zone["ip"], zone["port"])
        result = send_and_receive(s, game_hex, OpType.START_GAME)
        if result["code"] != 200:
            print(f"❌ 启动游戏失败: {result['message']}")
            return
        print(f"🎫 游戏 ticket: {result['data']}")

        # 注册
        print("\n🌟 模拟注册账号")
        reg_hex = build_hex(OpType.REGISTER, "yuxiang110", "newpass123", "q?", "a!")
        result = send_and_receive(s, reg_hex, OpType.REGISTER)
        if result["code"] == 200:
            print("🎉 注册成功")
        else:
            print(f"❌ 注册失败: {result['message']}")

        # 找回密码
        print("\n🌟 模拟找回密码")
        rec_hex = build_hex(OpType.RECOVER, "yuxiang110", "123456", "q?", "a!")
        result = send_and_receive(s, rec_hex, OpType.RECOVER)
        if result["code"] == 200:
            print("🎉 找回密码成功")
        else:
            print(f"❌ 找回密码失败: {result['message']}")

if __name__ == "__main__":
    main()
