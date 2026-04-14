# MCC module queries

1. **What is the largest executable module loaded in memory?**
   - rw_largest: 600.0M

2. **Which DLL contains the AI, physics, and damage code for Halo 2?**
   - halo2.dll holds Halo 2 campaign code — AI, physics, damage

3. **What is the base address of the mcc-win64-shipping.exe module?**
   - mcc-win64-shipping.exe @ 0x7ff79f3d0000 size=67.2M path=E:\SteamLibrar
path=E:\SteamLibrary\steamapps\common\Halo The Master Chief Collection\mcc\
Collection\mcc\binaries\win64\mcc-win64-shipping.exe

4. **Which DLL is the launcher/menu/engine shell for MCC?**
   - mcc-win64-shipping.exe is the launcher/menu/engine shell

5. **What is the size of the libcef.dll module?**
   - libcef.dll @ 0x7ff945240000 size=95.0M path=E:\SteamLibrary\steamapps\
path=E:\SteamLibrary\steamapps\common\Halo The Master Chief Collection\Engi
Collection\Engine\Binaries\ThirdParty\Cef\Win64\Cef\x86_64\libcef.dll

# MCC cross-references

1. **The halo2.dll module is part of the Halo 2 game files.**
   - install tree — extensions by total bytes
   - .map: 48 files, 23.90G
   - install tree — top 40 files by size
   - groundhog\maps\shared.map (1.30G, .map)
   - file-type decoder:
     - .map — mission data (AI scripts, geometry, scripts, tags)

2. **The MCC-WindowsNoEditor.pak file is likely used by the mcc-win64-shipp
mcc-win64-shipping.exe module.**
   - install tree — extensions by total bytes
   - .pak: 1 files, 10.18G
   - install tree — top 40 files by size
   - MCC\Content\Paks\MCC-WindowsNoEditor.pak (10.18G, .pak)
   - file-type decoder:
     - .pak / .uasset — packaged assets

3. **The PhysX3_x64.dll module is part of the Physics engine used in severa
several games.**
   - install tree — extensions by total bytes
   - .dll: 14 files, 2.28G
   - install tree — top 40 files by size
   - PhysX3_x64.dll (200.7M, .dll)
   - file-type decoder:
     - .dll — native code (reverse-engineering target)

# Fields to add to future dumps

1. **PE section headers:**
   - This would provide detailed information about the sections within each
each DLL and EXE, such as text, data, and bss.

2. **Exported symbols:**
   - Listing exported functions and variables from each module can help ide
identify entry points and API usage.

3. **DLL imports:**
   - Detailed list of imported functions from other modules or libraries us
used by each DLL and EXE to understand dependencies and function calls.