# Halo MCC — game data dump

Generated: 2026-04-14T03:50:50.000Z
MCC PID: not running
Install: E:\SteamLibrary\steamapps\common\Halo The Master Chief Collection

## install tree — extensions by total bytes
- .map: 48 files, 23.90G
- .pck: 14 files, 19.68G
- .fsb: 26 files, 11.12G
- .pak: 1 files, 10.18G
- .bk2: 22 files, 9.21G
- .dat: 3 files, 2.83G
- .bik: 4 files, 1.62G
- .ipak: 2 files, 1.29G

## install tree — top 40 files by size

file-type decoder:
- .map — mission data (AI scripts, geometry, scripts, tags)
- .dll — native code (reverse-engineering target)
- .bik — bink video cutscenes
- .fmod / .bank — FMOD audio
- .pak / .uasset — packaged assets

- halo2\preload\paks\shared.pck (12.25G, .pck)
- MCC\Content\Paks\MCC-WindowsNoEditor.pak (10.18G, .pak)
- halo4\sound\pc\sfxstream.pck (1.63G, .pck)
- halo2\h2_maps_win64_dx11\sounds_remastered.dat (1.44G, .dat)
- groundhog\maps\shared.map (1.30G, .map)
- halo1\sound\pc\sounds_music.fsb (912.8M, .fsb)
- halo3\maps\shared.map (892.5M, .map)
- halo2\h2_maps_win64_dx11\sounds_neutral.dat (883.4M, .dat)
- MCC\Content\Movies\FMS_MainMenu_v2.bk2 (831.8M, .bk2)
- groundhog\maps\ca_zanzibar.map (828.7M, .map)
- halo4\maps\m60_rescue.map (819.6M, .map)
- groundhog\maps\ca_relic.map (815.0M, .map)
- halo3odst\fmod\pc\sfx.fsb (804.8M, .fsb)
- groundhog\maps\ca_sanctuary.map (738.0M, .map)
- halo4\maps\m020.map (731.0M, .map)
- groundhog\maps\ca_coagulation.map (725.1M, .map)
- halo4\maps\m80_delta.map (703.0M, .map)
- halo4\maps\m30_cryptum.map (700.1M, .map)
- halo3\fmod\pc\sfx.fsb (690.9M, .fsb)
- haloreach\fmod\pc\sfx.fsb (678.9M, .fsb)
- groundhog\sound\pc\sfxbank.pck (671.4M, .pck)
- halo1\prebuild\paks\inplace2.ipak (664.6M, .ipak)
- halo1\prebuild\paks\inplace1.ipak (660.3M, .ipak)
- groundhog\maps\ca_lockout.map (647.2M, .map)
- halo4\maps\m90_sacrifice.map (640.1M, .map)
- halo4\maps\m40_invasion.map (628.2M, .map)
- halo4\spops_videos\H4_Ep11.bk2 (618.6M, .bk2)
- halo4\sound\pc\italian\soundstream.pck (584.5M, .pck)
- groundhog\maps\ca_warlock.map (581.6M, .map)
- halo4\sound\pc\spanish(spain)\soundstream.pck (579.2M, .pck)
- halo4\sound\pc\spanish(mexico)\soundstream.pck (571.5M, .pck)
- halo4\sound\pc\german\soundstream.pck (570.1M, .pck)
- halo3\maps\100_citadel.map (565.3M, .map)
- halo4\bink\ending_60.bik (553.1M, .bik)
- halo4\sound\pc\french(france)\soundstream.pck (547.5M, .pck)
- halo4\maps\shared.map (544.3M, .map)
- halo4\sound\pc\english(us)\soundstream.pck (542.1M, .pck)
- halo4\maps\m10_crash.map (541.4M, .map)
- halo2\h2_maps_win64_dx11\textures.dat (538.7M, .dat)
- halo3\maps\070_waste.map (525.0M, .map)

## save directory — recent files
save_dir: C:\Users\Ken\AppData\LocalLow\MCC\Temporary
- campaigncarnagereport1_3528_0_0.xml (2K, mtime=2026-04-14T01:38:25.000Z)

## reverse-engineering plan — what to look for
- health / shield floats: scan halo2.dll data section for 0.0–100.0 range floats that change under damage
- AI state: look for per-enemy structs near player pointer; likely 200–800 bytes each with team_id byte + alert_state + target_ref
- damage-apply function: AOB for MUL/FSUB on a float, CMP with zero, branch to death anim — patchable to NOP for invincibility
- squad coord: elites share a combat_group_id, editable via a single byte flip to break their coordination
- cheat floor: any address found via delta scan on shield value is a CANDIDATE; confirm with 2nd rescan after a different damage event
