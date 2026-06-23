#!/usr/bin/env python3
from pathlib import Path
import sys

from mtproxy_phase_contract import ENDPOINT_EXACT, ENDPOINT_NETWORK, endpoint_key_phases, rotation_phases


ROOT = Path(__file__).resolve().parents[1]
JAVA_ROOT = ROOT / "TMessagesProj/src/main/java/org/telegram"
MESSENGER = JAVA_ROOT / "messenger"

ENDPOINT_KEY = MESSENGER / "ProxyEndpointKey.java"
EVENT = MESSENGER / "ProxyConnectionEvent.java"
POLICY = MESSENGER / "ProxyPhasePolicy.java"
STORE = MESSENGER / "ProxyRuntimeStateStore.java"
SCHEDULER = MESSENGER / "ProxyCheckScheduler.java"
ROTATION = MESSENGER / "ProxyRotationController.java"
CONNECTIONS = JAVA_ROOT / "tgnet/ConnectionsManager.java"
DIAGNOSTICS = MESSENGER / "ProxyCheckDiagnostics.java"


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def require_file(path: Path, failures: list[str]) -> str:
    text = read(path)
    if not text:
        failures.append(f"{path.relative_to(ROOT)}: missing control-plane file")
    return text


def require(text: str, needle: str, message: str, failures: list[str]) -> None:
    if needle not in text:
        failures.append(message)


def require_not(text: str, needle: str, message: str, failures: list[str]) -> None:
    if needle in text:
        failures.append(message)


def main() -> int:
    failures: list[str] = []

    endpoint_key = require_file(ENDPOINT_KEY, failures)
    event = require_file(EVENT, failures)
    policy = require_file(POLICY, failures)
    store = require_file(STORE, failures)
    scheduler = read(SCHEDULER)
    rotation = read(ROTATION)
    connections = read(CONNECTIONS)
    diagnostics = read(DIAGNOSTICS)

    require(endpoint_key, "public final class ProxyEndpointKey", "ProxyEndpointKey must own endpoint identity helpers", failures)
    require(endpoint_key, "exact(SharedConfig.ProxyInfo", "ProxyEndpointKey must expose exact identity", failures)
    require(endpoint_key, "network(SharedConfig.ProxyInfo", "ProxyEndpointKey must expose host:port/network identity", failures)
    require(endpoint_key, "liveStage(SharedConfig.ProxyInfo", "ProxyEndpointKey must expose native live-stage identity", failures)
    require(endpoint_key, "matchesLiveStage", "ProxyEndpointKey must reject stale endpoint/secret native events", failures)
    require(endpoint_key, "secretDomainForLiveStage", "ProxyEndpointKey must keep ee domain matching with native endpoint keys", failures)

    require(event, "public final class ProxyConnectionEvent", "ProxyConnectionEvent must normalize connection-stage inputs", failures)
    require(event, "SOURCE_NATIVE_STAGE", "ProxyConnectionEvent must distinguish native-stage events", failures)
    require(event, "SOURCE_PROXY_CHECK", "ProxyConnectionEvent must distinguish proxy-check results", failures)
    require(event, "SOURCE_CONNECTED", "ProxyConnectionEvent must distinguish generic connected observations", failures)
    require(event, "SOURCE_CONNECT_START", "ProxyConnectionEvent must distinguish explicit connect attempts", failures)
    require(event, "ProxyCheckDiagnostics.normalize", "ProxyConnectionEvent must normalize phases at construction", failures)

    require(policy, "public final class ProxyPhasePolicy", "ProxyPhasePolicy must centralize phase decisions", failures)
    require(policy, "public enum Kind", "ProxyPhasePolicy must model phase kind", failures)
    require(policy, "public enum KeyScope", "ProxyPhasePolicy must model endpoint key scope", failures)
    require(policy, "usableSuccess", "ProxyPhasePolicy must mark usable-success phases", failures)
    require(policy, "canBackoff", "ProxyPhasePolicy must decide endpoint backoff centrally", failures)
    require(policy, "canRotate", "ProxyPhasePolicy must decide rotation centrally", failures)
    require(policy, "canOverwriteVisible", "ProxyPhasePolicy must decide visible overwrite centrally", failures)
    require(policy, "FIRST_TLS_APP_RECV", "ProxyPhasePolicy must treat first TLS app recv as usable success", failures)
    require(policy, "FIRST_MTPROXY_PACKET_RECV", "ProxyPhasePolicy must treat first MTProxy packet recv as usable success", failures)
    require(policy, "SERVER_HELLO_HMAC_OK", "ProxyPhasePolicy must explicitly classify server hello as handshake only", failures)

    for phase in sorted(endpoint_key_phases(ENDPOINT_NETWORK)):
        require(policy, f'case ProxyCheckDiagnostics.{phase.upper()}'.replace("NETWORK_BLOCK_SUSPECTED", "NETWORK_BLOCK_SUSPECTED"), f"ProxyPhasePolicy must assign network key scope for {phase}", failures)
    for phase in sorted(rotation_phases()):
        require(policy, phase.upper(), f"ProxyPhasePolicy must include rotation phase {phase}", failures)

    require(store, "public final class ProxyRuntimeStateStore", "ProxyRuntimeStateStore must own mutable runtime proxy health", failures)
    require(store, "HashMap<String, EndpointState> endpointStates", "ProxyRuntimeStateStore must own endpoint state outside ProxyCheckScheduler", failures)
    require(store, "USABLE_SUCCESS_HOLD_MS", "ProxyRuntimeStateStore must keep a short usable-success hold window", failures)
    require(store, "held_by_usable_success", "usable success followed by sibling failure must be held/shadowed", failures)
    require(store, "decision=backoff", "terminal failures without usable success must record backoff decisions", failures)
    require(store, "decision=ignored_stale_endpoint", "stale endpoint/secret native events must be ignored", failures)
    require(store, "decision=visible_only", "non-terminal live stages should be visible-only decisions", failures)
    require(store, "decision=rotation_trigger", "rotation-triggering failures must be explicit decisions", failures)
    require(store, "clearEndpointBackoff", "usable success must clear exact and network endpoint backoff", failures)
    require(store, "shouldScheduleFallback", "rotation must ask the store whether a fallback should be scheduled", failures)
    require(store, "isSwitchableCandidate", "rotation candidate filtering must be delegated to the store", failures)
    require(store, "appliedDiagnosticForProxyCheck", "proxy-check failures must preserve fresh concrete visible phases", failures)
    require(store, "markConnectionStarting", "explicit connect_start must be centralized in runtime store", failures)

    require(scheduler, "ProxyRuntimeStateStore.isFresh(proxyInfo)", "ProxyCheckScheduler.isFresh must delegate to ProxyRuntimeStateStore", failures)
    require(scheduler, "ProxyRuntimeStateStore.isEndpointBackedOff(proxyInfo)", "ProxyCheckScheduler.isEndpointBackedOff must delegate to ProxyRuntimeStateStore", failures)
    require(scheduler, "ProxyRuntimeStateStore.markConnected(proxyInfo)", "ProxyCheckScheduler.markConnected must delegate to ProxyRuntimeStateStore", failures)
    require(scheduler, "ProxyRuntimeStateStore.markEndpointFailure(proxyInfo, diagnostic)", "ProxyCheckScheduler.markEndpointFailure must delegate live failures to ProxyRuntimeStateStore", failures)
    require_not(scheduler, "HashMap<String, EndpointState> endpointStates", "ProxyCheckScheduler must not own endpoint backoff state after control-plane split", failures)
    require_not(scheduler, "private static String endpointStateKeyForDiagnostic", "ProxyCheckScheduler must not own phase key-scope policy", failures)

    require(connections, "ProxyConnectionEvent.nativeStage", "ConnectionsManager must build a normalized native-stage event", failures)
    require(connections, "ProxyRuntimeStateStore.onNativeStage", "ConnectionsManager must bridge native stages into ProxyRuntimeStateStore", failures)
    require_not(connections, "currentProxy.lastCheckDiagnostic = normalizedDiagnostic", "ConnectionsManager must not write visible diagnostics directly", failures)
    require_not(connections, "ProxyCheckScheduler.markEndpointFailure(currentProxy", "ConnectionsManager must not decide live endpoint backoff directly", failures)

    require(rotation, "ProxyRuntimeStateStore.isSwitchableCandidate(info)", "ProxyRotationController must ask store for switchable candidates", failures)
    require(rotation, "ProxyRuntimeStateStore.shouldScheduleFallback", "ProxyRotationController must ask store before scheduling terminal fallback", failures)
    require(rotation, "ProxyRuntimeStateStore.markConnectionStarting(info)", "ProxyRotationController must publish connect_start through the store", failures)
    require_not(rotation, "ProxyCheckDiagnostics.shouldAccelerateProxyRotation(diagnostic)", "ProxyRotationController must not use raw diagnostic rotation policy", failures)
    require_not(rotation, "ProxyCheckDiagnostics.hasFreshFailure(info)", "ProxyRotationController candidate filtering must not duplicate store policy", failures)

    require(diagnostics, "ProxyPhasePolicy.isFailure", "ProxyCheckDiagnostics must delegate failure classification to ProxyPhasePolicy", failures)
    require(diagnostics, "ProxyPhasePolicy.isLivePhase", "ProxyCheckDiagnostics must delegate live classification to ProxyPhasePolicy", failures)
    require(diagnostics, "ProxyPhasePolicy.shouldAccelerateProxyRotation", "ProxyCheckDiagnostics must delegate rotation classification to ProxyPhasePolicy", failures)
    require(diagnostics, "ProxyPhasePolicy.isProxyUsableSuccessPhase", "ProxyCheckDiagnostics must delegate usable-success classification to ProxyPhasePolicy", failures)

    if failures:
        print("Proxy control-plane policy guard failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("Proxy control-plane policy guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
