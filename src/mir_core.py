# -*- coding: utf-8 -*-
"""mir-eternal AccountServer 的 UDP 文本协议客户端。

协议(所有报文均为 UTF-8 文本,空格分隔):
    请求:  <seq> <op> <args...>
    响应:  <seq> <code> <args...>
      op=0 登录:   <seq> 0 user pass
                   -> 成功 <seq> 0 user pass <区服列表>   (每行 "ip,port/name", \\n 分隔)
                   -> 失败 <seq> 1 <错误信息>
      op=1 注册:   <seq> 1 user pass question answer
                   -> 成功 <seq> 2 user pass
                   -> 失败 <seq> 3 <错误信息>
                   (用户名 6-12 位字母开头 [A-Za-z0-9_], 密码 6-18, 密保问题/答案 2-18)
      op=2 改密:   <seq> 2 user newpass question answer
                   -> 成功 <seq> 4 ...
                   -> 失败 <seq> 5 <code>
      op=3 进场:   <seq> 3 user pass <区服名>
                   -> 成功 <seq> 6 user pass <ticket>     (同时 AccountServer 会把
                      "ticket;account" 通过 UDP 直发给 GameServer 的门票端口)
                   -> 失败 <seq> 7 <错误信息>
"""

import socket

from login_core import GameClient, OpType, build_hex


def create_client(protocol, server_ip, server_port):
    """按配置创建统一的登录客户端: 'udp' = mir-eternal AccountServer, 'tcp' = 旧版二进制协议。"""
    if str(protocol).lower() == "tcp":
        return LegacyTcpClient(server_ip, server_port)
    return MirEternalClient(server_ip, server_port)


class LegacyTcpClient:
    """旧版 TCP 二进制协议适配器, 接口与 MirEternalClient 对齐。"""

    def __init__(self, server_ip, server_port):
        self._client = GameClient(server_ip, server_port)

    def connect(self):
        self._client.connect()

    def close(self):
        self._client.close()

    def login(self, user, password):
        result = self._client.send_and_receive(build_hex(OpType.LOGIN, user, password), OpType.LOGIN)
        if result["code"] == 200:
            self._user, self._password = user, password
        return result

    def register(self, user, password, question, answer):
        return self._client.send_and_receive(build_hex(OpType.REGISTER, user, password, question, answer), OpType.REGISTER)

    def recover(self, user, new_password, question, answer):
        return self._client.send_and_receive(build_hex(OpType.RECOVER, user, new_password, question, answer), OpType.RECOVER)

    def start_game(self, zone):
        return self._client.send_and_receive(build_hex(OpType.START_GAME, zone["ip"], zone["port"]), OpType.START_GAME)


class MirEternalClient:
    """与 login_core.GameClient 等价的 UDP 版客户端, 返回同样的 {code, data|message} 结构。"""

    # 每个操作对应的成功响应码
    SUCCESS_CODES = {0: 0, 1: 2, 2: 4, 3: 6}

    def __init__(self, server_ip, server_port, timeout=5.0):
        self.server_addr = (server_ip, int(server_port))
        self.timeout = timeout
        self._seq = 0
        self._user = None
        self._password = None
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.timeout)

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    # ---------- 对外操作 ----------

    def login(self, user, password):
        """登录并返回区服列表 [{ip, port, name}]"""
        result = self._request(0, [user, password])
        if result["code"] == 200:
            self._user, self._password = user, password
        return result

    def register(self, user, password, question, answer):
        return self._request(1, [user, password, question, answer])

    def recover(self, user, new_password, question, answer):
        """通过密保问题修改密码"""
        return self._request(2, [user, new_password, question, answer])

    def start_game(self, zone):
        """取得进场门票(服务端会同时把门票推给游戏服), zone 为登录返回的区服字典。"""
        if not self._user:
            return {"code": 500, "message": "请先登录"}
        return self._request(3, [self._user, self._password, zone["name"]])

    # ---------- 内部 ----------

    def _request(self, op, args):
        if not self.sock:
            self.connect()

        self._seq += 1
        payload = f"{self._seq} {op} " + " ".join(str(a) for a in args)

        data = None
        for attempt in (1, 2):  # UDP 可能丢包, 重试一次
            try:
                self.sock.sendto(payload.encode("utf-8"), self.server_addr)
                data, _ = self.sock.recvfrom(4096)
                break
            except socket.timeout:
                continue

        if data is None:
            return {"code": 500, "message": "服务器无响应, 请确认 AccountServer 已启动"}

        text = data.decode("utf-8", errors="replace").strip()
        parts = text.split(" ")
        if len(parts) < 2:
            return {"code": 500, "message": "响应格式错误: " + text[:80]}

        try:
            seq, code = int(parts[0]), int(parts[1])
        except ValueError:
            return {"code": 500, "message": "响应格式错误: " + text[:80]}

        if seq != self._seq:
            return {"code": 500, "message": "响应序号不匹配, 请重试"}

        expected = self.SUCCESS_CODES.get(op)
        if code != expected:
            return {"code": 500, "message": " ".join(parts[2:]) or f"服务器返回错误码 {code}"}

        if op == 0:
            # <seq> 0 user pass 区服列表(取第 5 段以后的全部, 避免区服名含空格被截断)
            return {"code": 200, "data": self._parse_zones(text)}
        if op == 3:
            # <seq> 6 user pass TICKET
            return {"code": 200, "data": parts[4] if len(parts) > 4 else ""}
        return {"code": 200, "data": " ".join(parts[2:])}

    @staticmethod
    def _parse_zones(text):
        zones = []
        rest = text.split(" ", 4)
        if len(rest) < 5:
            return zones
        for line in rest[4].replace("\r", "").split("\n"):
            line = line.strip()
            if not line or "/" not in line or "," not in line:
                continue
            ip_port, name = line.split("/", 1)
            ip, port = ip_port.split(",", 1)
            zones.append({"ip": ip, "port": port, "name": name})
        return zones
