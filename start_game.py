import subprocess

exe_path = r"C:\baidunetdiskdownload\CQYH_10424\Binaries\Win64\MMOGame-Win64-Shipping.exe"
server_ip = "192.168.1.3"
server_port = "8701"
area_name = "局域网"
ticket = "FHXY-wVEnh4owBkgrkpC2QdDiFg9IxO7MR4rb"

args = (
    f"-wegame=1,1,{server_ip},{server_port},1,1,{server_ip},{server_port},{area_name} "
    f"/ip:1,1,{server_ip} "
    f"/port:{server_port} "
    f"/ticket:{ticket} "
    f"/AreaName:{area_name}"
)

print("✅ 启动命令:")
print(f"{exe_path} {args}")

# 启动游戏
subprocess.Popen([exe_path] + args.split(), shell=True)
