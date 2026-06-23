package org.telegram.messenger;

import android.os.SystemClock;

public final class ProxyConnectionEvent {

    public static final String SOURCE_NATIVE_STAGE = "native_stage";
    public static final String SOURCE_PROXY_CHECK = "proxy_check";
    public static final String SOURCE_CONNECTED = "connected";
    public static final String SOURCE_CONNECT_START = "connect_start";

    public final String source;
    public final int account;
    public final String phase;
    public final String endpointKey;
    public final long timestamp;

    private ProxyConnectionEvent(String source, int account, String phase, String endpointKey, long timestamp) {
        this.source = source;
        this.account = account;
        this.phase = ProxyCheckDiagnostics.normalize(phase);
        this.endpointKey = endpointKey == null ? "" : endpointKey;
        this.timestamp = timestamp == 0 ? SystemClock.elapsedRealtime() : timestamp;
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey) {
        return nativeStage(account, phase, endpointKey, SystemClock.elapsedRealtime());
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey, long timestamp) {
        return new ProxyConnectionEvent(SOURCE_NATIVE_STAGE, account, phase, endpointKey, timestamp);
    }

    public static ProxyConnectionEvent proxyCheck(int account, SharedConfig.ProxyInfo proxyInfo, String phase) {
        return new ProxyConnectionEvent(SOURCE_PROXY_CHECK, account, phase, ProxyEndpointKey.liveStage(proxyInfo), SystemClock.elapsedRealtime());
    }

    public static ProxyConnectionEvent connected(int account, SharedConfig.ProxyInfo proxyInfo) {
        return new ProxyConnectionEvent(SOURCE_CONNECTED, account, ProxyCheckDiagnostics.OK, ProxyEndpointKey.liveStage(proxyInfo), SystemClock.elapsedRealtime());
    }

    public static ProxyConnectionEvent connectStart(int account, SharedConfig.ProxyInfo proxyInfo) {
        return new ProxyConnectionEvent(SOURCE_CONNECT_START, account, ProxyCheckDiagnostics.CONNECT_START, ProxyEndpointKey.liveStage(proxyInfo), SystemClock.elapsedRealtime());
    }
}
