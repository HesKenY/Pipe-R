## Windows volume control via Core Audio API
##
## Usage:
##   volume.ps1 get                          # returns {system, spotify}
##   volume.ps1 set <system|app> <0..1>      # app defaults to Spotify.exe
##   volume.ps1 set-app <name> <0..1>        # specific process name
##
## Uses inline C# to call IAudioEndpointVolume (master) and
## IAudioSessionManager2 -> ISimpleAudioVolume (per-process). Zero deps
## beyond what ships with Windows.
##
## Emits compact JSON on stdout for the server to forward.

param(
    [Parameter(Mandatory=$true)][ValidateSet('get','set','set-app')][string]$Action,
    [string]$Target,
    [double]$Value = -1.0
)

try {
    Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioEndpointVolume {
    int RegisterControlChangeNotify(IntPtr n);
    int UnregisterControlChangeNotify(IntPtr n);
    int GetChannelCount(out uint c);
    int SetMasterVolumeLevel(float v, Guid ctx);
    int SetMasterVolumeLevelScalar(float v, Guid ctx);
    int GetMasterVolumeLevel(out float v);
    int GetMasterVolumeLevelScalar(out float v);
    int SetChannelVolumeLevel(uint ch, float v, Guid ctx);
    int SetChannelVolumeLevelScalar(uint ch, float v, Guid ctx);
    int GetChannelVolumeLevel(uint ch, out float v);
    int GetChannelVolumeLevelScalar(uint ch, out float v);
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool m, Guid ctx);
    int GetMute(out bool m);
}

[Guid("87CE5498-68D6-44E5-9215-6DA47EF883D8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface ISimpleAudioVolume {
    int SetMasterVolume(float v, Guid ctx);
    int GetMasterVolume(out float v);
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool m, Guid ctx);
    int GetMute(out bool m);
}

[Guid("F4B1A599-7266-4319-A8CA-E70ACB11E8CD"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioSessionControl {
    int GetState(out int state);
    int GetDisplayName([MarshalAs(UnmanagedType.LPWStr)] out string name);
    int SetDisplayName([MarshalAs(UnmanagedType.LPWStr)] string name, Guid ctx);
    int GetIconPath([MarshalAs(UnmanagedType.LPWStr)] out string path);
    int SetIconPath([MarshalAs(UnmanagedType.LPWStr)] string path, Guid ctx);
    int GetGroupingParam(out Guid g);
    int SetGroupingParam(Guid g, Guid ctx);
    int RegisterAudioSessionNotification(IntPtr n);
    int UnregisterAudioSessionNotification(IntPtr n);
}

[Guid("BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioSessionControl2 {
    // IAudioSessionControl methods:
    int GetState(out int state);
    int GetDisplayName([MarshalAs(UnmanagedType.LPWStr)] out string name);
    int SetDisplayName([MarshalAs(UnmanagedType.LPWStr)] string name, Guid ctx);
    int GetIconPath([MarshalAs(UnmanagedType.LPWStr)] out string path);
    int SetIconPath([MarshalAs(UnmanagedType.LPWStr)] string path, Guid ctx);
    int GetGroupingParam(out Guid g);
    int SetGroupingParam(Guid g, Guid ctx);
    int RegisterAudioSessionNotification(IntPtr n);
    int UnregisterAudioSessionNotification(IntPtr n);
    // IAudioSessionControl2 additions:
    int GetSessionIdentifier([MarshalAs(UnmanagedType.LPWStr)] out string id);
    int GetSessionInstanceIdentifier([MarshalAs(UnmanagedType.LPWStr)] out string id);
    int GetProcessId(out uint pid);
    int IsSystemSoundsSession();
    int SetDuckingPreference([MarshalAs(UnmanagedType.Bool)] bool opt);
}

[Guid("E2F5BB11-0570-40CA-ACDD-3AA01277DEE8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioSessionEnumerator {
    int GetCount(out int count);
    int GetSession(int index, out IAudioSessionControl s);
}

[Guid("77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioSessionManager2 {
    int GetAudioSessionControl(Guid eventContext, int streamFlags, out IAudioSessionControl s);
    int GetSimpleAudioVolume(Guid eventContext, int streamFlags, out ISimpleAudioVolume v);
    int GetSessionEnumerator(out IAudioSessionEnumerator e);
    int RegisterSessionNotification(IntPtr n);
    int UnregisterSessionNotification(IntPtr n);
    int RegisterDuckNotification(string id, IntPtr n);
    int UnregisterDuckNotification(IntPtr n);
}

[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDevice {
    int Activate(ref Guid id, int clsCtx, IntPtr p, [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface);
    int OpenPropertyStore(int access, out IntPtr store);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
    int GetState(out int state);
}

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceEnumerator {
    int EnumAudioEndpoints(int dataFlow, int mask, out IntPtr devices);
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
    int GetDevice(string id, out IMMDevice dev);
    int RegisterEndpointNotificationCallback(IntPtr n);
    int UnregisterEndpointNotificationCallback(IntPtr n);
}

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
public class MMDeviceEnumeratorComObject { }

public static class Volume {
    static readonly Guid IID_IAudioEndpointVolume = new Guid("5CDF2C82-841E-4546-9722-0CF74078229A");
    static readonly Guid IID_IAudioSessionManager2 = new Guid("77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F");

    static IMMDevice DefaultDevice() {
        var mde = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        IMMDevice dev = null;
        mde.GetDefaultAudioEndpoint(0, 1, out dev);
        return dev;
    }

    public static float GetSystem() {
        var dev = DefaultDevice();
        var iid = IID_IAudioEndpointVolume;
        object o;
        dev.Activate(ref iid, 7, IntPtr.Zero, out o);
        var v = (IAudioEndpointVolume)o;
        float s;
        v.GetMasterVolumeLevelScalar(out s);
        return s;
    }

    public static void SetSystem(float v) {
        var dev = DefaultDevice();
        var iid = IID_IAudioEndpointVolume;
        object o;
        dev.Activate(ref iid, 7, IntPtr.Zero, out o);
        var vol = (IAudioEndpointVolume)o;
        if (v < 0) v = 0; if (v > 1) v = 1;
        vol.SetMasterVolumeLevelScalar(v, Guid.Empty);
    }

    public static float GetApp(string processName) {
        var dev = DefaultDevice();
        var iid = IID_IAudioSessionManager2;
        object o;
        dev.Activate(ref iid, 7, IntPtr.Zero, out o);
        var mgr = (IAudioSessionManager2)o;
        IAudioSessionEnumerator sessions;
        mgr.GetSessionEnumerator(out sessions);
        int count;
        sessions.GetCount(out count);
        for (int i = 0; i < count; i++) {
            IAudioSessionControl sc;
            sessions.GetSession(i, out sc);
            var sc2 = (IAudioSessionControl2)sc;
            uint pid;
            sc2.GetProcessId(out pid);
            if (pid == 0) continue;
            try {
                var p = Process.GetProcessById((int)pid);
                if (p.ProcessName.Equals(processName, StringComparison.OrdinalIgnoreCase)) {
                    var sav = (ISimpleAudioVolume)sc;
                    float lvl;
                    sav.GetMasterVolume(out lvl);
                    return lvl;
                }
            } catch { }
        }
        return -1f;
    }

    public static bool SetApp(string processName, float v) {
        if (v < 0) v = 0; if (v > 1) v = 1;
        var dev = DefaultDevice();
        var iid = IID_IAudioSessionManager2;
        object o;
        dev.Activate(ref iid, 7, IntPtr.Zero, out o);
        var mgr = (IAudioSessionManager2)o;
        IAudioSessionEnumerator sessions;
        mgr.GetSessionEnumerator(out sessions);
        int count;
        sessions.GetCount(out count);
        bool found = false;
        for (int i = 0; i < count; i++) {
            IAudioSessionControl sc;
            sessions.GetSession(i, out sc);
            var sc2 = (IAudioSessionControl2)sc;
            uint pid;
            sc2.GetProcessId(out pid);
            if (pid == 0) continue;
            try {
                var p = Process.GetProcessById((int)pid);
                if (p.ProcessName.Equals(processName, StringComparison.OrdinalIgnoreCase)) {
                    var sav = (ISimpleAudioVolume)sc;
                    sav.SetMasterVolume(v, Guid.Empty);
                    found = true;
                }
            } catch { }
        }
        return found;
    }
}
'@

    $appName = if ($Target) { $Target } else { 'Spotify' }

    switch ($Action) {
        'get' {
            $sys = [Volume]::GetSystem()
            $app = [Volume]::GetApp($appName)
            $result = [ordered]@{
                ok = $true
                system = [Math]::Round($sys, 4)
                app = $appName
                appVolume = if ($app -ge 0) { [Math]::Round($app, 4) } else { $null }
            }
            $result | ConvertTo-Json -Compress
        }
        'set' {
            if ($Target -eq 'system') {
                [Volume]::SetSystem([float]$Value)
                '{"ok":true,"target":"system","value":' + [Math]::Round($Value, 4) + '}'
            } elseif ($Target -eq 'app') {
                $ok = [Volume]::SetApp($appName, [float]$Value)
                '{"ok":' + $ok.ToString().ToLower() + ',"target":"app","app":"' + $appName + '","value":' + [Math]::Round($Value, 4) + '}'
            } else {
                '{"ok":false,"error":"target must be system or app"}'
            }
        }
        'set-app' {
            $ok = [Volume]::SetApp($appName, [float]$Value)
            '{"ok":' + $ok.ToString().ToLower() + ',"target":"app","app":"' + $appName + '","value":' + [Math]::Round($Value, 4) + '}'
        }
    }
} catch {
    '{"ok":false,"error":"' + ($_.Exception.Message -replace '"','\"' -replace '\\','\\\\') + '"}'
}
