"""Constants for Sony Bravia TV (IP Control)."""
from __future__ import annotations

DOMAIN = "sony_bravia_ip"
MANUFACTURER = "Sony"

CONF_PSK = "psk"
CONF_SOURCES = "sources"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "Sony TV"
DEFAULT_SCAN_INTERVAL = 10  # seconds
STATIC_REFRESH = 1800  # seconds between input/app list refreshes

SOURCE_INPUT = "input"
SOURCE_APP = "app"

# Fallback IRCC codes, used when the TV does not report its own list.
DEFAULT_IRCC_CODES: dict[str, str] = {
    "Power": "AAAAAQAAAAEAAAAVAw==",
    "PowerOff": "AAAAAQAAAAEAAAAvAw==",
    "WakeUp": "AAAAAQAAAAEAAAAuAw==",
    "Home": "AAAAAQAAAAEAAABgAw==",
    "Return": "AAAAAgAAAJcAAAAjAw==",
    "Exit": "AAAAAQAAAAEAAABjAw==",
    "Confirm": "AAAAAQAAAAEAAABlAw==",
    "Up": "AAAAAQAAAAEAAAB0Aw==",
    "Down": "AAAAAQAAAAEAAAB1Aw==",
    "Left": "AAAAAQAAAAEAAAA0Aw==",
    "Right": "AAAAAQAAAAEAAAAzAw==",
    "Options": "AAAAAgAAAJcAAAA2Aw==",
    "Display": "AAAAAQAAAAEAAAA6Aw==",
    "Input": "AAAAAQAAAAEAAAAlAw==",
    "GGuide": "AAAAAQAAAAEAAAAOAw==",
    "Guide": "AAAAAgAAAKQAAABbAw==",
    "VolumeUp": "AAAAAQAAAAEAAAASAw==",
    "VolumeDown": "AAAAAQAAAAEAAAATAw==",
    "Mute": "AAAAAQAAAAEAAAAUAw==",
    "ChannelUp": "AAAAAQAAAAEAAAAQAw==",
    "ChannelDown": "AAAAAQAAAAEAAAARAw==",
    "Play": "AAAAAgAAAJcAAAAaAw==",
    "Pause": "AAAAAgAAAJcAAAAZAw==",
    "Stop": "AAAAAgAAAJcAAAAYAw==",
    "Next": "AAAAAgAAAJcAAAA9Aw==",
    "Prev": "AAAAAgAAAJcAAAA8Aw==",
    "Rewind": "AAAAAgAAAJcAAAAbAw==",
    "Forward": "AAAAAgAAAJcAAAAcAw==",
    "SubTitle": "AAAAAgAAAJcAAAAoAw==",
    "Audio": "AAAAAQAAAAEAAAAXAw==",
    "Red": "AAAAAgAAAJcAAAAlAw==",
    "Green": "AAAAAgAAAJcAAAAmAw==",
    "Yellow": "AAAAAgAAAJcAAAAnAw==",
    "Blue": "AAAAAgAAAJcAAAAkAw==",
    "Netflix": "AAAAAgAAABoAAAB8Aw==",
    "Num1": "AAAAAQAAAAEAAAAAAw==",
    "Num2": "AAAAAQAAAAEAAAABAw==",
    "Num3": "AAAAAQAAAAEAAAACAw==",
    "Num4": "AAAAAQAAAAEAAAADAw==",
    "Num5": "AAAAAQAAAAEAAAAEAw==",
    "Num6": "AAAAAQAAAAEAAAAFAw==",
    "Num7": "AAAAAQAAAAEAAAAGAw==",
    "Num8": "AAAAAQAAAAEAAAAHAw==",
    "Num9": "AAAAAQAAAAEAAAAIAw==",
    "Num0": "AAAAAQAAAAEAAAAJAw==",
}

# Aliases so users can type friendly names in remote.send_command
IRCC_ALIASES: dict[str, str] = {
    "back": "Return",
    "ok": "Confirm",
    "enter": "Confirm",
    "select": "Confirm",
    "menu": "Home",
    "info": "Display",
    "previous": "Prev",
    "rev": "Rewind",
    "ff": "Forward",
    "subtitle": "SubTitle",
}
