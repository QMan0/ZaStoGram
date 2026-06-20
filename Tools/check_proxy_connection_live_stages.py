#!/usr/bin/env python3
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "diagnostics": ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/ProxyCheckDiagnostics.java",
    "connections_java": ROOT / "TMessagesProj/src/main/java/org/telegram/tgnet/ConnectionsManager.java",
    "notification_center": ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/NotificationCenter.java",
    "proxy_list": ROOT / "TMessagesProj/src/main/java/org/telegram/ui/ProxyListActivity.java",
    "values": ROOT / "TMessagesProj/src/main/res/values/strings.xml",
    "values_ru": ROOT / "TMessagesProj/src/main/res/values-ru/strings.xml",
    "defines": ROOT / "TMessagesProj/jni/tgnet/Defines.h",
    "wrapper": ROOT / "TMessagesProj/jni/TgNetWrapper.cpp",
    "socket": ROOT / "TMessagesProj/jni/tgnet/ConnectionSocket.cpp",
    "socket_h": ROOT / "TMessagesProj/jni/tgnet/ConnectionSocket.h",
    "collector": ROOT / "Tools/collect_mtproxy_logs.ps1",
}

LIVE_PHASES = [
    "admission_queue",
    "host_resolve_start",
    "connect_start",
    "socket_connect_start",
    "socket_connected",
    "client_hello_sent",
    "server_hello_hmac_ok",
    "on_connected",
    "first_tls_app_sent",
    "first_tls_app_recv",
]


def text(name: str) -> str:
    return FILES[name].read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    diagnostics = text("diagnostics")
    combined = "\n".join(text(name) for name in FILES)

    for phase in LIVE_PHASES:
        require(phase in diagnostics, f"ProxyCheckDiagnostics must define live phase '{phase}'")
        require(phase in text("socket") or phase in text("connections_java"), f"live phase '{phase}' must be emitted or consumed")

    require(
        "isLivePhase" in diagnostics
        and "hasFreshLivePhase" in diagnostics
        and "ProxyStatusHostResolve" in diagnostics
        and "ProxyStatusClientHelloSent" in diagnostics
        and "ProxyStatusServerHelloOk" in diagnostics,
        "ProxyCheckDiagnostics must map live native stages to user-facing status text",
    )
    header_idx = diagnostics.find("public static String headerStatusText")
    header_checking_idx = diagnostics.find("if (proxyInfo.checking)", header_idx)
    header_live_idx = diagnostics.find("if (hasFreshLivePhase(proxyInfo))", header_idx)
    require(
        header_idx >= 0
        and header_live_idx >= 0
        and header_checking_idx >= 0
        and header_live_idx < header_checking_idx,
        "proxy window header must show fresh live stages before generic checking text",
    )
    require(
        "proxyConnectionStageChanged" in text("notification_center")
        and "onProxyConnectionStageChanged" in text("connections_java")
        and "NotificationCenter.proxyConnectionStageChanged" in text("connections_java"),
        "Java must expose a NotificationCenter event for current proxy live stages",
    )
    require(
        "onProxyConnectionStageChanged" in text("defines")
        and "jclass_ConnectionsManager_onProxyConnectionStageChanged" in text("wrapper")
        and 'GetStaticMethodID(jclass_ConnectionsManager, "onProxyConnectionStageChanged", "(ILjava/lang/String;)V")' in text("wrapper"),
        "JNI bridge must forward native proxy live stages to ConnectionsManager",
    )
    require(
        "publishProxyConnectionStage" in text("socket_h")
        and "publishProxyConnectionStage(" in text("socket")
        and "!overrideProxyAddress.empty()" in text("socket")
        and 'publishProxyConnectionStage("host_resolve_start")' in text("socket")
        and 'publishProxyConnectionStage("client_hello_sent")' in text("socket")
        and 'publishProxyConnectionStage("server_hello_hmac_ok")' in text("socket")
        and 'publishProxyConnectionStage("first_tls_app_recv")' in text("socket"),
        "ConnectionSocket must publish live stages at the same boundaries it logs",
    )
    require(
        "addObserver(this, NotificationCenter.proxyConnectionStageChanged)" in text("proxy_list")
        and "removeObserver(this, NotificationCenter.proxyConnectionStageChanged)" in text("proxy_list")
        and "id == NotificationCenter.proxyConnectionStageChanged" in text("proxy_list"),
        "Proxy list must refresh header and current row on live proxy stage updates",
    )
    require(
        "proxy_connection_stage" in text("collector"),
        "live Java proxy stages must be collected into mtproxy marker logs",
    )
    for name in ("values", "values_ru"):
        source = text(name)
        for string_name in (
            "ProxyStatusAdmissionQueue",
            "ProxyStatusHostResolve",
            "ProxyStatusTcpConnecting",
            "ProxyStatusTcpConnected",
            "ProxyStatusClientHelloSent",
            "ProxyStatusServerHelloOk",
            "ProxyStatusMtprotoStarting",
            "ProxyStatusFirstDataSent",
            "ProxyStatusFirstDataReceived",
        ):
            require(f'name="{string_name}"' in source, f"{name} must define {string_name}")

    print("Proxy live connection stages guard passed.")


if __name__ == "__main__":
    main()
