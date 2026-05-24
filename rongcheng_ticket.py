import pyautogui
import time
import keyboard
import tkinter as tk
from PIL import ImageGrab, ImageTk
import threading
import urllib.request
import json
import os

# =========================
# 全局紧急终止快捷键（Ctrl+Shift+Q 立即杀死进程）
# =========================

keyboard.add_hotkey("ctrl+shift+q", lambda: os._exit(0))
print("提示：任何时候按 Ctrl+Shift+Q 可强制终止脚本")

# =========================
# 坐标配置
# =========================

# 绿色RGB 由后面取色步骤动态设置
TARGET_RGB = None

# RGB容差
TOLERANCE = 20

# 绿色区域最小像素数：低于此值视为噪点忽略
GREEN_AREA_MIN = 500

# 绿色占比基准：首次检测到的绿色按钮记为"确认"（无票），之后占比明显低于基准的为"支付"（抢到）
BASELINE_RATIO = None

# =========================
# PushPlus 配置
# =========================

PUSHPLUS_TOKEN = input("请输入 PushPlus Token（没有则按回车跳过）：").strip()

if PUSHPLUS_TOKEN:
    print("已配置 PushPlus 推送")
else:
    print("未配置 PushPlus，仅本地提醒")

# =========================
# 点击「立即下单」按钮定位
# =========================

print("\n请将鼠标移动到「立即下单」按钮上方，然后按 Enter")

submit_x = submit_y = None

def on_move(event):
    global submit_x, submit_y
    submit_x, submit_y = event.x, event.y

root = tk.Tk()
root.attributes("-fullscreen", True)
root.attributes("-alpha", 0.3)
root.focus_force()

label = tk.Label(
    root,
    text="移动鼠标到「立即下单」按钮上，按 Enter 确认",
    font=("Microsoft YaHei", 16),
    fg="white",
    bg="black",
)
label.pack(pady=50)

root.bind("<Motion>", on_move)

# 用 keyboard 库全局监听 Enter，避免 tkinter 窗口焦点问题
def wait_enter():
    keyboard.wait("enter")
    root.quit()

threading.Thread(target=wait_enter, daemon=True).start()

root.mainloop()
root.destroy()

SUBMIT_X, SUBMIT_Y = submit_x, submit_y
print(f"立即下单按钮坐标：({SUBMIT_X}, {SUBMIT_Y})")

# =========================
# 框选检测区域
# =========================

print("\n请用鼠标框选绿色按钮可能出现的区域")

root = tk.Tk()
root.attributes("-fullscreen", True)
root.attributes("-alpha", 0.3)

canvas = tk.Canvas(root, cursor="cross")
canvas.pack(fill=tk.BOTH, expand=True)

start_x = start_y = end_x = end_y = 0

def on_press(event):
    global start_x, start_y
    start_x = event.x
    start_y = event.y

def on_drag(event):
    canvas.delete("rect")
    canvas.create_rectangle(
        start_x,
        start_y,
        event.x,
        event.y,
        outline="red",
        width=2,
        tag="rect"
    )

def on_release(event):
    global end_x, end_y
    end_x = event.x
    end_y = event.y
    root.quit()

canvas.bind("<ButtonPress-1>", on_press)
canvas.bind("<B1-Motion>", on_drag)
canvas.bind("<ButtonRelease-1>", on_release)

root.mainloop()
root.destroy()

SCAN_REGION = (
    min(start_x, end_x),
    min(start_y, end_y),
    max(start_x, end_x),
    max(start_y, end_y)
)

print("监测区域：", SCAN_REGION)

# =========================
# 绿色RGB 取色
# =========================

print("\n请在网站上触发一次弹窗（让绿色按钮出现），然后按 Enter 取色")

keyboard.wait("enter")

sample_img = ImageGrab.grab(bbox=SCAN_REGION)

root = tk.Tk()
root.title("请点击绿色按钮区域")
root.focus_force()

tk_img = ImageTk.PhotoImage(sample_img)
canvas = tk.Canvas(root, width=sample_img.width, height=sample_img.height, cursor="cross")
canvas.pack()
canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

samp_rgb = (0, 0, 0)

def on_click(event):
    global samp_rgb
    samp_rgb = sample_img.getpixel((event.x, event.y))
    root.quit()

canvas.bind("<Button-1>", on_click)

root.mainloop()
root.destroy()

TARGET_RGB = samp_rgb
print(f"采样绿色 RGB: {TARGET_RGB}")

# =========================
# 基本设置
# =========================

pyautogui.FAILSAFE = True

print("===========================================")
print(" 成都蓉城抢票脚本 作者: UserJCY ")
print("===========================================")

while True:
    try:
        delay = int(input("请输入多少秒后开始抢票："))
        if delay >= 0:
            break
        print("请输入有效的非负整数")
    except ValueError:
        print("请输入有效的整数")

print(f"\n脚本将在 {delay} 秒后开始")
print("按 F8 可停止（循环间隙检测）")
print("按 Ctrl+Shift+Q 可随时强制终止（推荐）")
print("鼠标移到左上角可强制停止")
print("===================================")

# =========================
# 倒计时
# =========================

for i in range(delay, 0, -1):

    print(f"倒计时：{i} 秒", end="\r")

    time.sleep(1)

print("\n开始抢票！")

# =========================
# PushPlus 推送
# =========================

def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN:
        return
    try:
        data = json.dumps({
            "token": PUSHPLUS_TOKEN,
            "title": title,
            "content": content,
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://www.pushplus.plus/send",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
        print("\n[PushPlus] 已发送手机推送")
    except Exception as e:
        print(f"\n[PushPlus] 发送失败: {e}")

# =========================
# 绿色区域识别：扫描找绿色按钮完整边界，计算绿色占比
# =========================

def analyze_green_button(img, start_x, start_y):
    """从起点扫描找到绿色按钮完整边界，统计区域内绿色占比"""
    width, height = img.size

    def is_green(px, py):
        r, g, b = img.getpixel((px, py))
        return (
            abs(r - TARGET_RGB[0]) <= TOLERANCE
            and abs(g - TARGET_RGB[1]) <= TOLERANCE
            and abs(b - TARGET_RGB[2]) <= TOLERANCE
        )

    # 在较大窗口内找所有绿色像素的 bbox（步长=2，快扫）
    search_l = max(0, start_x - 350)
    search_r = min(width, start_x + 350)
    search_t = max(0, start_y - 100)
    search_b = min(height, start_y + 100)

    gx_min, gx_max = start_x, start_x
    gy_min, gy_max = start_y, start_y
    found_any = False

    for y in range(search_t, search_b, 2):
        for x in range(search_l, search_r, 2):
            if is_green(x, y):
                found_any = True
                gx_min = min(gx_min, x)
                gx_max = max(gx_max, x)
                gy_min = min(gy_min, y)
                gy_max = max(gy_max, y)

    if not found_any:
        return (start_x, start_y, start_x, start_y), 0.0

    # 在 bbox 内逐像素精确统计绿色占比
    green_count = 0
    for y in range(gy_min, gy_max + 1):
        for x in range(gx_min, gx_max + 1):
            if is_green(x, y):
                green_count += 1

    bbox = (gx_min, gy_min, gx_max, gy_max)
    bbox_area = (gx_max - gx_min + 1) * (gy_max - gy_min + 1)
    ratio = green_count / bbox_area if bbox_area > 0 else 0
    return bbox, ratio

# =========================
# 本地报警弹窗
# =========================

def alarm_popup():
    win = tk.Tk()
    win.title("抢到票了！")
    win.attributes("-topmost", True)

    # 窗口居中
    w, h = 420, 200
    ws = win.winfo_screenwidth()
    hs = win.winfo_screenheight()
    x = (ws - w) // 2
    y = (hs - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    end_time = time.time() + 300  # 5分钟

    tk.Label(
        win,
        text="已抢到票！请立即支付！",
        font=("Microsoft YaHei", 18, "bold"),
        fg="red",
    ).pack(pady=(20, 10))

    timer_label = tk.Label(
        win,
        text="剩余支付时间：5:00",
        font=("Microsoft YaHei", 14),
    )
    timer_label.pack(pady=5)

    tk.Label(
        win,
        text="票不付钱 5 分钟即作废！",
        font=("Microsoft YaHei", 10),
        fg="gray",
    ).pack(pady=5)

    def update_timer():
        if not win.winfo_exists():
            return
        remaining = int(end_time - time.time())
        if remaining <= 0:
            timer_label.config(text="剩余支付时间：0:00  已超时！", fg="red")
        else:
            m, s = divmod(remaining, 60)
            timer_label.config(text=f"剩余支付时间：{m}:{s:02d}")
            if remaining < 60:
                timer_label.config(fg="red")
            win.after(1000, update_timer)

    def on_close():
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_close)

    update_timer()

    win.mainloop()

count = 0

# =========================
# 主循环
# =========================

GRABBED = False

while True:

    try:

        # =========================
        # F8 / 鼠标左上角停止
        # =========================

        if keyboard.is_pressed("F8"):
            print("\n检测到 F8，脚本已停止")
            break

        mx, my = pyautogui.position()
        if mx < 3 and my < 3:
            print("\n鼠标移到左上角，脚本已停止")
            break

        # =========================
        # 点击立即下单
        # =========================

        pyautogui.click(SUBMIT_X, SUBMIT_Y)

        # 等待服务器响应
        time.sleep(0.35)

        # =========================
        # 截图监测区域
        # =========================

        img = ImageGrab.grab(bbox=SCAN_REGION)

        width, height = img.size

        green_x, green_y = None, None

        # =========================
        # 扫描绿色像素
        # =========================

        for x in range(0, width, 8):

            # 扫描中途也响应停止
            if keyboard.is_pressed("F8"):
                break

            mx, my = pyautogui.position()
            if mx < 3 and my < 3:
                break

            for y in range(0, height, 8):

                r, g, b = img.getpixel((x, y))

                if (
                    abs(r - TARGET_RGB[0]) <= TOLERANCE
                    and abs(g - TARGET_RGB[1]) <= TOLERANCE
                    and abs(b - TARGET_RGB[2]) <= TOLERANCE
                ):

                    green_x, green_y = x, y
                    break

            if green_x is not None:
                break

        # =========================
        # 发现绿色按钮 → 分析是"确认"还是"支付"
        # =========================

        if green_x is not None:

            # 找完整绿色区域，计算绿色占比
            (bx1, by1, bx2, by2), ratio = analyze_green_button(img, green_x, green_y)

            # 绿色区域面积（像素数）
            area = (bx2 - bx1 + 1) * (by2 - by1 + 1)
            if area < GREEN_AREA_MIN:
                time.sleep(0.1)
                continue

            # 按钮中心点（相对于截图的坐标，转换到屏幕绝对坐标）
            center_x = SCAN_REGION[0] + (bx1 + bx2) // 2
            center_y = SCAN_REGION[1] + (by1 + by2) // 2

            if BASELINE_RATIO is None:
                # 首次检测到绿色 → 记为"确认"基准
                BASELINE_RATIO = ratio
                pyautogui.click(center_x, center_y)
                count += 1
                print(f"\n首次检测到绿色按钮，基准占比: {BASELINE_RATIO:.3f}")
                print(f"已尝试 {count} 次（无票）")
                time.sleep(0.08)

            elif ratio < BASELINE_RATIO * 0.97:
                # 绿色占比明显低于基准 → "发送到手机微信支付" → 抢到了！
                pyautogui.click(center_x, center_y)
                count += 1

                print(f"\n{'='*50}")
                print(f" 检测到支付窗口！重试 {count} 次后抢到！")
                print(f" 绿色占比: {ratio:.3f}（基准: {BASELINE_RATIO:.3f}）")
                print(f"{'='*50}")

                # 手机推送
                threading.Thread(
                    target=send_pushplus,
                    args=(
                        "成都蓉城抢票提醒 - 已抢到！",
                        f"支付窗口已弹出！请立即在 {time.strftime('%H:%M:%S')} 之前完成支付，超过5分钟未付款订单将作废！"
                    ),
                    daemon=True,
                ).start()

                # 弹出本地报警窗口
                GRABBED = True
                alarm_popup()
                break

            else:
                # 绿色占比与基准接近 → "确认"按钮 → 无票
                pyautogui.click(center_x, center_y)
                count += 1
                print(f"\r已尝试 {count} 次（无票，占比: {ratio:.3f}）", end="")
                time.sleep(0.08)

        else:

            # 没发现绿色按钮，说明正在等待（加载中或还没弹窗）
            count += 1
            if count % 20 == 0:
                print(f"\r正在刷票... 已尝试 {count} 次", end="")
            time.sleep(0.1)

    # =========================
    # 鼠标左上角强制停止
    # =========================

    except pyautogui.FailSafeException:

        print("\n鼠标触发强制停止")
        break

    except Exception as e:

        print("\n错误：", e)

if GRABBED:
    print("\n抢票流程结束，请尽快支付！")
