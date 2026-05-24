# Rongcheng Ticket Bot

Screen-based color detection tool for snatching Chengdu Rongcheng FC match tickets.

## How to Use

```bash
pip install -r requirements.txt
python rongcheng_ticket.py
```

Follow the prompts:

1. Enter PushPlus token for WeChat notifications (optional)
2. Move mouse over the purchase button and press Enter
3. Drag to select the region where green buttons appear
4. Trigger a popup on the website, press Enter, then click on the green button to sample its color
5. Enter countdown delay in seconds

## How It Works

- Repeatedly clicks the purchase button
- Takes screenshots of the selected region and scans for green pixels
- First detected green button is saved as the baseline ("confirm" = sold out)
- If a later green button has significantly lower green-ratio than baseline, it's the payment window
- Sends PushPlus WeChat notification and shows a local countdown alert

## How to Stop

- **Ctrl+Shift+Q** — Emergency kill switch (always works)
- F8 — Stops between cycles
- Move mouse to top-left corner — PyAutoGUI failsafe
