# 成都蓉城抢票脚本

基于屏幕颜色检测的自动化抢票工具，用于成都蓉城足球俱乐部比赛门票。

## 使用方法

```bash
pip install pyautogui keyboard pillow
python rongcheng_ticket.py
```

按提示依次完成：
1. 输入 PushPlus Token（微信推送通知，可选）
2. 鼠标移到「立即下单」按钮 → 按 Enter
3. 框选绿色按钮出现的区域
4. 触发一次弹窗 → 按 Enter → 点击绿色按钮取色
5. 输入倒计时秒数

## 工作原理

- 循环点击「立即下单」按钮
- 截图检测区域，扫描绿色像素
- 首次检测到的绿色按钮记为基准（"确认" = 无票）
- 后续绿色占比明显低于基准 → 判定为支付窗口 → 抢到票
- PushPlus 微信推送 + 本地倒计时弹窗双重提醒

## 停止方式

- **Ctrl+Shift+Q** — 随时强制终止
- F8 — 循环间隙中停止
- 鼠标移到屏幕左上角 — pyautogui failsafe
