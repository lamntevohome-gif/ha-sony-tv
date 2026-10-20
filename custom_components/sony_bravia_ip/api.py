"""Async client for the Sony Bravia REST API (JSON-RPC) and IRCC."""
from __future__ import annotations

import asyncio
import itertools
import logging
import socket
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

IRCC_BODY = (
    '<?xml version="1.0"?>'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
    's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
    "<s:Body>"
    '<u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1">'
    "<IRCCCode>{code}</IRCCCode>"
    "</u:X_SendIRCC>"
    "</s:Body>"
    "</s:Envelope>"
)


class SonyBraviaError(Exception):
    """Generic API error."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class SonyBraviaConnectionError(SonyBraviaError):
    """TV unreachable."""


class SonyBraviaAuthError(SonyBraviaError):
    """Pre-Shared Key rejected."""


class SonyBraviaClient:
    """Minimal async client for Sony Bravia TVs (2013+ Android/Google TV)."""

    def __init__(
        self,
        host: str,
        psk: str,
        session: aiohttp.ClientSession,
        timeout: float = 8,
    ) -> None:
        self.host = host
        self._psk = psk
        self._session = session
        self._timeout = timeout
        self._ids = itertools.count(1)

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-Auth-PSK": self._psk}

    # ------------------------------------------------------------------ core
    async def _rpc(
        self,
        service: str,
        method: str,
        params: dict[str, Any] | None = None,
        version: str = "1.0",
    ) -> list[Any]:
        payload = {
            "method": method,
            "id": next(self._ids),
            "params": [params] if params is not None else [],
            "version": version,
        }
        url = f"http://{self.host}/sony/{service}"
        try:
            async with asyncio.timeout(self._timeout):
                async with self._session.post(
                    url, json=payload, headers=self._headers
                ) as resp:
                    if resp.status in (401, 403):
                        raise SonyBraviaAuthError("Invalid Pre-Shared Key", resp.status)
                    data = await resp.json(content_type=None)
        except SonyBraviaError:
            raise
        except (aiohttp.ClientError, TimeoutError, OSError, ValueError) as err:
            raise SonyBraviaConnectionError(f"{method}: {err}") from err

        if not isinstance(data, dict):
            raise SonyBraviaError(f"{method}: unexpected response")
        if "error" in data:
            err = data["error"]
            code = err[0] if err else None
            msg = err[1] if len(err) > 1 else ""
            if code in (401, 403):
                raise SonyBraviaAuthError(f"{method}: {msg}", code)
            raise SonyBraviaError(f"{method}: [{code}] {msg}", code)
        return data.get("result") or data.get("results") or []

    async def _rpc_versions(
        self, service: str, method: str, params: dict[str, Any] | None, versions: list[str]
    ) -> list[Any]:
        """Try several API versions (newest first)."""
        last: SonyBraviaError | None = None
        for ver in versions:
            try:
                return await self._rpc(service, method, params, ver)
            except (SonyBraviaConnectionError, SonyBraviaAuthError):
                raise
            except SonyBraviaError as err:
                last = err
        assert last is not None
        raise last

    # ---------------------------------------------------------------- system
    async def get_system_info(self) -> dict[str, Any]:
        res = await self._rpc("system", "getSystemInformation")
        return res[0] if res else {}

    async def get_power_status(self) -> bool:
        res = await self._rpc("system", "getPowerStatus")
        return bool(res) and res[0].get("status") == "active"

    async def set_power(self, on: bool) -> None:
        await self._rpc("system", "setPowerStatus", {"status": on})

    async def reboot(self) -> None:
        await self._rpc("system", "requestReboot")

    async def get_remote_codes(self) -> dict[str, str]:
        res = await self._rpc("system", "getRemoteControllerInfo")
        codes: dict[str, str] = {}
        if len(res) > 1 and isinstance(res[1], list):
            for item in res[1]:
                if "name" in item and "value" in item:
                    codes[item["name"]] = item["value"]
        return codes

    # ----------------------------------------------------------------- audio
    async def get_volume_info(self) -> list[dict[str, Any]]:
        res = await self._rpc("audio", "getVolumeInformation")
        return res[0] if res else []

    async def set_volume(self, volume: int | str, target: str = "speaker") -> None:
        await self._rpc(
            "audio", "setAudioVolume", {"target": target, "volume": str(volume)}
        )

    async def set_mute(self, mute: bool) -> None:
        await self._rpc("audio", "setAudioMute", {"status": mute})

    async def get_sound_setting(self, target: str = "outputTerminal") -> dict[str, Any] | None:
        res = await self._rpc_versions(
            "audio", "getSoundSettings", {"target": target}, ["1.1"]
        )
        return res[0][0] if res and res[0] else None

    async def set_sound_setting(self, target: str, value: str) -> None:
        await self._rpc(
            "audio",
            "setSoundSettings",
            {"settings": [{"target": target, "value": value}]},
            "1.1",
        )

    # --------------------------------------------------------------- picture
    async def get_picture_setting(self, target: str = "pictureMode") -> dict[str, Any] | None:
        res = await self._rpc("video", "getPictureQualitySettings", {"target": target})
        return res[0][0] if res and res[0] else None

    async def set_picture_setting(self, target: str, value: str) -> None:
        await self._rpc(
            "video",
            "setPictureQualitySettings",
            {"settings": [{"target": target, "value": str(value)}]},
        )

    # ------------------------------------------------------------- avContent
    async def get_external_inputs(self) -> list[dict[str, Any]]:
        res = await self._rpc_versions(
            "avContent", "getCurrentExternalInputsStatus", None, ["1.1", "1.0"]
        )
        return res[0] if res else []

    async def get_playing_content(self) -> dict[str, Any] | None:
        """Return what is playing; None when an app is in foreground."""
        try:
            res = await self._rpc("avContent", "getPlayingContentInfo")
        except (SonyBraviaConnectionError, SonyBraviaAuthError):
            raise
        except SonyBraviaError:
            return None
        return res[0] if res else None

    async def set_play_content(self, uri: str) -> None:
        await self._rpc("avContent", "setPlayContent", {"uri": uri})

    async def get_content_list(self, source: str, count: int = 100) -> list[dict[str, Any]]:
        res = await self._rpc_versions(
            "avContent",
            "getContentList",
            {"source": source, "stIdx": 0, "cnt": count},
            ["1.5", "1.2", "1.0"],
        )
        return res[0] if res else []

    # ------------------------------------------------------------ appControl
    async def get_apps(self) -> list[dict[str, Any]]:
        res = await self._rpc("appControl", "getApplicationList")
        return res[0] if res else []

    async def set_active_app(self, uri: str) -> None:
        await self._rpc("appControl", "setActiveApp", {"uri": uri})

    async def terminate_apps(self) -> None:
        await self._rpc("appControl", "terminateApps")

    # ------------------------------------------------------------------ IRCC
    async def send_ircc(self, code: str) -> None:
        headers = {
            **self._headers,
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPACTION": '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"',
        }
        try:
            async with asyncio.timeout(self._timeout):
                async with self._session.post(
                    f"http://{self.host}/sony/IRCC",
                    data=IRCC_BODY.format(code=code),
                    headers=headers,
                ) as resp:
                    if resp.status in (401, 403):
                        raise SonyBraviaAuthError("Invalid Pre-Shared Key", resp.status)
                    if resp.status >= 400:
                        raise SonyBraviaError(f"IRCC failed: HTTP {resp.status}", resp.status)
        except SonyBraviaError:
            raise
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            raise SonyBraviaConnectionError(f"IRCC: {err}") from err


def send_wol(mac: str, broadcast: str = "255.255.255.255") -> None:
    """Send a Wake-on-LAN magic packet (blocking, run in executor)."""
    clean = mac.replace(":", "").replace("-", "").replace(".", "")
    if len(clean) != 12:
        raise ValueError(f"Invalid MAC address: {mac}")
    packet = bytes.fromhex("FF" * 6 + clean * 16)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (broadcast, 9))
