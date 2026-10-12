"""Start the game client through the Windows shell so its requireAdministrator manifest is honored.

subprocess.Popen cannot start an executable that requires elevation (WinError 740). The shell "open"
verb shows the normal UAC prompt instead, like double-clicking the exe.
"""
import os
import subprocess
from pathlib import Path


def build_command(exe_path, zone, ticket):
    exe = Path(exe_path).resolve()
    if not exe.is_file():
        raise FileNotFoundError(f"未找到游戏客户端：{exe}")
    port = int(zone["port"])
    if not 1 <= port <= 65535:
        raise ValueError("游戏端口无效")
    ip = str(zone["ip"]).strip()
    area = str(zone["name"])
    if not ip or any(c.isspace() for c in ip):
        raise ValueError("游戏服务器地址无效")
    if any(c in area for c in "\r\n\0"):
        raise ValueError("区服名称含无效字符")
    if not ticket or any(c.isspace() or c == "\0" for c in ticket):
        raise ValueError("游戏门票为空或格式无效")
    args = [
        f"-wegame=1,1,{ip},{port},1,1,{ip},{port},{area}",
        f"/ip:1,1,{ip}",
        f"/port:{port}",
        f"/ticket:{ticket}",
        f"/AreaName:{area}",
    ]
    # Client root (…/Binaries/Win64/x.exe -> …), where the original launcher lives.
    return str(exe), subprocess.list2cmdline(args), str(exe.parents[2])


def start_game(exe_path, zone, ticket):
    exe, arguments, cwd = build_command(exe_path, zone, ticket)
    os.startfile(exe, operation="open", arguments=arguments, cwd=cwd, show_cmd=1)
