# Halo 2 health pinning
## Where the player health/shield floats live
Unit struct inside `halo2.dll` data section, offsets likely in 0x100-0x400 
range from struct base.

### Three ways to FIND them:
1. **Vision-read HUD + delta scan**: Use vision reader to inspect HUD value
values and perform a delta scan on shield value.
2. **Pointer chase from player biped**: Follow the player's biped pointer c
chain to find the health/shield unit struct.
3. **AOB scan for known movss instructions**: Search for `movss` instructio
instructions near the damage path that modify the health/shield values.

### Why writing 9999 works (Halo 2 doesn't clamp health on read)
Writing a value of 9999 to the health/shield address allows the game to dis
display an infinite shield, as Halo 2 does not clamp health values when rea
reading them.

### Why it might get overwritten by next frame
However, the game may still clamp the health value when applying damage. To
To prevent this, we can pin the value every 80ms loop.

## halo_health_pin.py outline

1. Open process using a debugger or memory reader.
2. Find addresses of the health/shield floats using one of the methods abov
above.
3. Create a threading.Thread that writes the maximum float value to the add
address every 80ms loop.

## Interaction with the aimbot
Health pinning allows Ken to face-tank while the aimbot dials in the headsh
headshot engine, making it easier to land critical shots.