
# ePoster Display System

A Raspberry Pi–based digital poster display system that automatically fetches, caches, and displays poster images from an API in a fullscreen slideshow.  
Designed for unattended operation in conferences, exhibitions, and kiosk-style displays.

---

## Features

- 🔄 **Automatic Internet Detection**: Works online or offline with cached data
- 📡 **API Integration**: Fetches posters and event data from REST APIs
- 🖼️ **Image Caching**: Intelligent local caching with automatic cleanup
- 🔁 **Auto-refresh**: Periodically updates poster list from API
- 🖱️ **Manual Override Menu**: Right-click to select posters manually
- 🎨 **Image Processing**: Automatic scaling and rotation
- ⚙️ **Configurable**: All settings in a single `config.json`
- 🖥️ **Fullscreen Display**: Optimized for portrait or landscape displays
- 🚀 **Auto-start on Boot**: Runs automatically using `systemd`
- ♻️ **Auto-Restart**: Restarts automatically if the app crashes

---

## System Requirements

### Hardware
- Raspberry Pi (3 / 4 / 5 recommended)
- HDMI display
- Mouse (for manual override)

### Operating System
- **Raspberry Pi OS (Desktop)**
  > Lite versions are not supported (no graphical environment)

### Software
- Python **3.9+**
- systemd
- X11 desktop environment

---

## Project Structure

```text
eposter/
├── eposterMenu.py          # Main application
├── requirements.txt        # Python dependencies
├── config.json             # Configuration file
├── api_handler.py          # API logic
├── cache_handler.py        # Image caching & processing
├── display_handler.py      # Pygame display utilities
├── wifi_connect.py         # Internet availability checks
├── fetch_event_data.py     # Event data fetching
├── eposter_cache/          # Cached poster images (auto-created)
├── api_data.json           # Cached API response
├── event_data.json         # Cached event data
└── README.md               # This file
````

---

## Installation

### 1. System Dependencies (Required for Pygame)

```bash
sudo apt update
sudo apt install -y \
  python3 python3-pip python3-venv \
  libsdl2-dev \
  libsdl2-image-dev \
  libsdl2-mixer-dev \
  libsdl2-ttf-dev
```

---

### 2. Project Setup

```bash
mkdir -p ~/eposter
cd ~/eposter
# Copy project files here
```

---

### 3. Python Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 4. Python Dependencies

Create `requirements.txt`:

```txt
pygame>=2.1.0
requests>=2.28.0
Pillow>=9.5.0
```

Install:

```bash
pip install -r requirements.txt
```

---

## Configuration

All configuration is done via `config.json`.

### Example `config.json`

```json
{
  "api": {
    "poster_token": "YOUR_API_TOKEN"
  },
  "display": {
    "display_time": 5,
    "device_id": "default_device"
  }
}
```

### Configuration Options

| Key            | Description                                 |
| -------------- | ------------------------------------------- |
| `poster_token` | **Required** API token for fetching posters |
| `display_time` | Time (seconds) each poster is shown         |
| `device_id`    | Identifier for the display/screen           |

---

## Running the Application

### Manual Run (Recommended First)

```bash
source venv/bin/activate
python3 eposterMenu.py
```

Expected behavior:

* Fullscreen display opens
* Posters rotate automatically
* Right-click opens the manual menu

---

## Manual Controls

| Action       | Result                   |
| ------------ | ------------------------ |
| Right-click  | Open manual menu         |
| Select image | Display selected poster  |
| Timed Poster | Return to scheduled mode |
| Exit         | Quit application         |

---

## Auto-Start on Boot (systemd)

### 1. Create the Service File

```bash
sudo nano /etc/systemd/system/eposter.service
```

Paste **exactly**:

```ini
[Unit]
Description=ePoster Display System
After=graphical.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=bhavy
WorkingDirectory=/home/bhavy/eposter
ExecStart=/home/bhavy/eposter/venv/bin/python /home/bhavy/eposter/eposterMenu.py
Restart=always
RestartSec=5
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/bhavy/.Xauthority

[Install]
WantedBy=graphical.target
```

> ⚠️ Replace `bhavy` with your username if different.

---

### 2. Enable and Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable eposter.service
sudo systemctl start eposter.service
```

---

### 3. Verify Status

```bash
systemctl status eposter.service
```

Expected output:

```
Active: active (running)
```

---

### 4. Reboot Test (Final Check)

```bash
sudo reboot
```

The application should start automatically after boot.

---

## Logging & Debugging

### Live Logs

```bash
journalctl -u eposter.service -f
```

### Logs for Current Boot

```bash
journalctl -u eposter.service -b
```

---

## Offline Mode

* Internet availability is detected automatically
* If offline:

  * Cached posters are used
  * Application continues running without blocking
* When internet returns:

  * API refresh resumes automatically

---

## How It Works

1. **Internet Check**: Detects whether internet is available
2. **API Fetch**: Downloads poster and event data when online
3. **Caching**: Images are cached locally in `eposter_cache/`
4. **Display**: Posters are shown fullscreen using Pygame
5. **Manual Override**: Right-click menu interrupts any running display
6. **Auto-refresh**: Data is refreshed periodically in the background

---

## Troubleshooting

### Service Not Starting

```bash
systemd-analyze verify /etc/systemd/system/eposter.service
```

### Black Screen on Boot

* Ensure Raspberry Pi OS Desktop is installed
* HDMI must be connected
* Check `DISPLAY=:0`

### No Posters Displaying

* Verify `poster_token` in `config.json`
* Check API accessibility
* Check cached images:

  ```bash
  ls eposter_cache/
  ```

---

## Maintenance

### Restart the Application

```bash
sudo systemctl restart eposter.service
```

### Update Code

```bash
# replace files or pull updates
sudo systemctl restart eposter.service
```

### Update Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

---

## License

[Add your license information here]

---

## Author

**Bhavy**
ePoster Display System – Raspberry Pi

```

---

If you want next, I can:
- tailor this for **public GitHub**
- add **kiosk hardening steps**
- generate a **PDF / DOC version**
- simplify it for **non-technical users**

Just tell me.
```
