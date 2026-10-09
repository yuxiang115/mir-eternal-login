# config.py

import os
import sys
import ctypes

if getattr(sys, 'frozen', False):
    # 如果是打包后的 EXE
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 如果是源码运行
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GAME_FOLDER_PATH = BASE_DIR

# 默认服务器配置
SERVER_IP = "127.0.0.1"  # 默认服务器 IP
SERVER_PORT = 7000

# 登录协议: udp = mir-eternal AccountServer, tcp = 旧版二进制协议
PROTOCOL = "udp"

# 默认操作模式（32 或 64）
GAME_OP = 32




# read config file from current directory if file not found, use default values and write to file
def read_config():
    """
    从配置文件读取服务器 IP、端口和操作模式
    如果文件不存在，使用默认值并写入配置文件
    """
    config_path = os.path.join(BASE_DIR, "login.ini")
    config = {
        "server_ip": SERVER_IP,
        "server_port": SERVER_PORT,
        "protocol": PROTOCOL,
        "game_op": GAME_OP
    }

    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            for key, value in config.items():
                f.write(f"{key}={value}\n")
        return config

    with open(config_path, 'r') as f:
        for line in f:
            key, value = line.strip().split('=', 1)
            config[key] = value

    return config



def get_exe_path(game_op=None):
    """
    根据选择返回完整的 exe 路径
    :param game_op: 可选，32 或 64，默认取配置值
    """
    if game_op is None:
        game_op = GAME_OP
    folder = f"Win{game_op}"

    safe_game_folder = GAME_FOLDER_PATH.strip().strip('"').strip("'").rstrip(r"\/")
    exe_path = os.path.join(safe_game_folder, "Binaries", folder, f"MMOGame-Win{game_op}-Shipping.exe")
    return exe_path



config = read_config()  # 初始化配置文件，如果不存在则创建
GAME_OP = config.get("game_op", GAME_OP)
SERVER_IP = config.get("server_ip", SERVER_IP)
SERVER_PORT = int(config.get("server_port", SERVER_PORT))
PROTOCOL = config.get("protocol", PROTOCOL)
GAME_FOLDER_PATH = config.get("game_path", GAME_FOLDER_PATH)
GAME_FOLDER_PATH = GAME_FOLDER_PATH.strip().strip('"').strip("'").rstrip(r"\/")
DEBUG = config.get("debug", "0") == "1"
print(f"✅ 读取配置: IP={SERVER_IP}, 端口={SERVER_PORT}, 协议={PROTOCOL}, 操作模式={GAME_OP}, 路径={GAME_FOLDER_PATH}, 调试模式={DEBUG}")


def show_console_if_debug(debug):
    if sys.platform.startswith("win"):
        if debug:
            ctypes.windll.kernel32.AllocConsole()
            sys.stdout = open("CONOUT$", "w")
            sys.stderr = open("CONOUT$", "w")
            print("调试模式：显示控制台")




