import ttkbootstrap as tb
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys
import hPyT


from login_core import GameClient, OpType, build_hex
from mir_core import create_client
from config import get_exe_path, SERVER_IP, SERVER_PORT, GAME_OP, DEBUG, PROTOCOL, show_console_if_debug


class GameLauncherUI:
    def __init__(self, master: tb.Window):
        self.master = master
        self.master.title("传奇永恒")
        self.master.resizable(False, False)
    
        win_w, win_h = int(420 * 1.2), int(540 * 1.2)
        pos_x = int((self.master.winfo_screenwidth() - win_w) / 2)
        pos_y = int((self.master.winfo_screenheight() - win_h) / 2)
        self.master.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.master.configure(bg="#0f0f10")

        # 字体放大 20%
        self.base_font = ("Microsoft YaHei", int(12 * 1.2))
        self.title_font = ("Microsoft YaHei", int(14 * 1.4), "bold")
        self.close_btn_font = ("Microsoft YaHei", int(14 * 1.2), "bold")

        self.button_font = self.base_font

        # 样式
        self.style = tb.Style()
        self.style.configure("Custom.TButton", font=self.button_font)
        self.style.configure("Custom.TCheckbutton", font=self.base_font)

        self.style.configure("Custom.Treeview", font=("Microsoft YaHei", 12), rowheight=40)
        self.style.configure("Custom.Treeview.Heading", font=("Microsoft YaHei", 14, "bold"))

        self.style.configure("SmallCheck.TCheckbutton", font=("Microsoft YaHei", 6))




        self.content_area = tb.Frame(master)
        self.content_area.pack(fill=BOTH, expand=True)



        self.client = create_client(PROTOCOL, SERVER_IP, SERVER_PORT)
        try:
            self.client.connect()
        except Exception as e:
            print(f"连接服务器失败 SERVER_IP={SERVER_IP}, SERVER_PORT={SERVER_PORT}: {e}")
            messagebox.showerror("无法连接服务器",
                                f"请检查网络连接或服务器状态\n检测配置文件 login.ini 是否正确\n")
            master.destroy()
            return

        self.user = None
        self.password = None

        master.bind("<Return>", lambda *_: self.on_login())
        self.create_login_ui()

    def _start_drag(self, event):
        if event.widget in self._no_drag_widgets:
            return
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root

    def _do_drag(self, event):
        if not hasattr(self, "_drag_start_x"):
            return
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        x = self.master.winfo_x() + dx
        y = self.master.winfo_y() + dy
        self.master.geometry(f"+{x}+{y}")
        self._drag_start_x, self._drag_start_y = event.x_root, event.y_root

    def create_login_ui(self):
        self.clear_ui_content()

        outer = tb.Frame(self.content_area, padding=(20, 80, 20, 20))
        outer.pack(expand=True, fill=BOTH)

        # 登录标题
        tb.Label(outer, text="登 录", font=self.title_font).pack(anchor="center", pady=(0, 20))

        frm = tb.Frame(outer)
        frm.pack(expand=True, fill=BOTH)

        self.entry_user = self._labeled_entry(frm, "账 号")
        self.entry_pass = self._labeled_entry(frm, "密 码", show="*")

        tb.Button(frm, text="✓ 登 录", bootstyle=PRIMARY, style="Custom.TButton",
                  command=self.on_login).pack(fill=X, pady=(50, 20))

        bottom = tb.Frame(frm)
        bottom.pack(fill=X, pady=5)

        tb.Button(bottom, text="👥 注 册", bootstyle=SECONDARY, style="Custom.TButton",
                  command=self.create_register_ui).pack(
            side=LEFT, expand=YES, fill=X, padx=(0, 5))
        tb.Button(bottom, text="🔒 找回密码", bootstyle=SECONDARY, style="Custom.TButton",
                  command=self.create_recover_ui).pack(
            side=RIGHT, expand=YES, fill=X, padx=(5, 0))

        self.entry_user.focus()

    def create_register_ui(self):
        self._account_form("注册账号", self.on_register)

    def create_recover_ui(self):
        self._account_form("找回密码", self.on_recover, recover=True)

    def create_zone_ui(self, zones):
        self.zones = zones
        self.clear_ui_content()

        frm = tb.Frame(self.content_area, padding=20)
        frm.pack(expand=True, fill=BOTH)

        tb.Label(frm, text="选择服务器", font=self.title_font).pack(anchor=W, pady=(0, 10))

        # 包裹 Treeview 的 Frame，控制高度
        tree_frame = tb.Frame(frm, height=360)  # 可以调整 460 为你想要的高度
        tree_frame.pack(fill=BOTH, expand=NO, pady=10)
        tree_frame.pack_propagate(False)

        self.tree = tb.Treeview(tree_frame, columns=("server",), show="headings", style="Custom.Treeview")
        self.tree.heading("server", text="服务器")
        self.tree.column("server", anchor=W)
        self.tree.pack(side=LEFT, fill=BOTH, expand=YES)

        class AutoScrollbar(tb.Scrollbar):
            def set(self, lo, hi):
                if float(lo) <= 0.0 and float(hi) >= 1.0:
                    self.pack_forget()
                else:
                    if not self.winfo_ismapped():
                        self.pack(side=RIGHT, fill=Y)
                super().set(lo, hi)

        # Treeview 和 AutoScrollbar
        scrollbar = AutoScrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)


        self.tree.configure(yscrollcommand=scrollbar.set)

        for z in zones:
            self.tree.insert("", END, values=(z["name"],))
        self.tree.selection_set(self.tree.get_children()[0])

        self.game_op_var = tk.IntVar(value=GAME_OP)

        chk = tb.Checkbutton(frm, text="启动64位", variable=self.game_op_var,
                            onvalue=64, offvalue=32, style="Custom.SmallCheck.TCheckbutton")
        chk.pack(anchor="w", pady=(0, 10))

        tb.Button(frm, text="进入游戏", bootstyle=SUCCESS, style="Custom.TButton",
                command=self.on_start_game).pack(fill=X, pady=5)
        tb.Button(frm, text="← 返回登录", bootstyle=SECONDARY, style="Custom.TButton",
                command=self.create_login_ui).pack(fill=X)

    def on_login(self):
        u, p = self.entry_user.get().strip(), self.entry_pass.get().strip()
        if not u or not p:
            return
        result = self.client.login(u, p)
        if result["code"] == 200:
            self.user, self.password = u, p
            if not result["data"]:
                messagebox.showerror("登录失败", "区服列表为空, 请检查 AccountServer 工作目录的 server 文件")
                return
            self.create_zone_ui(result["data"])
        else:
            messagebox.showerror("登录失败", result["message"])

    def on_register(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        q = self.entry_q.get().strip()
        a = self.entry_a.get().strip()
        result = self.client.register(u, p, q, a)
        if result["code"] == 200:
            messagebox.showinfo("注册成功", "注册成功！")
            self.create_login_ui()
        else:
            messagebox.showerror("注册失败", result["message"] + "\n\n(要求: 账号6-12位字母开头, 密码6-18位, 密保问题和答案2-18位)")

    def on_recover(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        q = self.entry_q.get().strip()
        a = self.entry_a.get().strip()
        result = self.client.recover(u, p, q, a)
        if result["code"] == 200:
            messagebox.showinfo("修改成功", "密码已修改")
            self.create_login_ui()
        else:
            messagebox.showerror("失败", result["message"])

    def on_start_game(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        zone_name = item["values"][0]
        zone = next((z for z in self.zones if z["name"] == zone_name), None)
        if not zone:
            return
        result = self.client.start_game(zone)
        if result["code"] == 200:
            self.launch_game(zone, result["data"])
        else:
            messagebox.showerror("启动失败", result["message"])

    def launch_game(self, zone, ticket):
        exe_path = get_exe_path(self.game_op_var.get())
        args = (
            f"-wegame=1,1,{zone['ip']},{zone['port']},1,1,{zone['ip']},{zone['port']},{zone['name']} "
            f"/ip:1,1,{zone['ip']} /port:{zone['port']} "
            f"/ticket:{ticket} /AreaName:{zone['name']}"
        )
        subprocess.Popen([exe_path] + args.split(), cwd=os.path.dirname(exe_path))

    def _labeled_entry(self, parent, text, **entry_kw):
        tb.Label(parent, text=text, font=self.base_font).pack(anchor=W, pady=(10, 4))
        ent = tb.Entry(parent, font=self.base_font, **entry_kw)
        ent.pack(fill=X)
        return ent

    def _account_form(self, title, ok_cmd, recover=False):
        self.clear_ui_content()

        frm = tb.Frame(self.content_area, padding=20)
        frm.pack(expand=True, fill=BOTH)

        tb.Label(frm, text=title, font=self.title_font).pack(pady=10)

        self.entry_user = self._labeled_entry(frm, "账 号")
        if recover:
            self.entry_pass = self._labeled_entry(frm, "新 密 码", show="*")
        else:
            self.entry_pass = self._labeled_entry(frm, "密 码", show="*")
        self.entry_q = self._labeled_entry(frm, "密保问题")
        self.entry_a = self._labeled_entry(frm, "密保答案")

        tb.Button(frm, text=title, bootstyle=PRIMARY, style="Custom.TButton",
                  command=ok_cmd).pack(fill=X, pady=10)
        tb.Button(frm, text="← 返回登录", bootstyle=SECONDARY, style="Custom.TButton",
                  command=self.create_login_ui).pack(fill=X)

        self.entry_user.focus()

    def clear_ui_content(self):
        for w in self.content_area.winfo_children():
            w.destroy()


if __name__ == "__main__":
    show_console_if_debug(DEBUG)
    game_exe_path = get_exe_path(game_op=GAME_OP)
    print(f"✅ 游戏执行文件路径: {game_exe_path}")
    if not os.path.isfile(game_exe_path):
        msg = f"未找到游戏执行文件\n请将登陆器放在游戏目录下"
        print(f"❌ {msg}")
        messagebox.showerror("启动失败", msg)
        sys.exit(1)
    
    root = tb.Window(themename="darkly")
    GameLauncherUI(root)
    root.mainloop()

