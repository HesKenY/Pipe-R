# Halo 2 .map format

## .map Header Layout
- magic: 4-byte identifier (e.g., "Halo")
- version: 4-byte integer
- tag_index_offset: 4-byte offset to the tag index table
- scenario_tag_index: 4-byte index into the tag index table for the scenari
scenario tag

## Mission Names and Campaign Levels
- groundhog\maps\shared.map: Shared assets across multiple levels
- groundhog\maps\ca_zanzibar.map: Zanzibar level
- groundhog\maps\ca_relic.map: Relic level
- groundhog\maps\ca_sanctuary.map: Sanctuary level
- groundhog\maps\ca_coagulation.map: Coagulation level
- groundhog\maps\ca_lockout.map: Lockout level
- groundhog\maps\ca_warlock.map: Warlock level

## HSC (Halo Script) Tag Type
- Contains compiled script bytecode for mission logic
- Linked to scenario tags for execution during gameplay

## Tag Types Relevant for Cheating
- ai_squad: Defines AI squad behavior and composition
- weapon: Describes weapon properties and effects
- projectile: Specifies projectile characteristics and damage
- damage_effect: Determines how damage is applied and visualized
- biped: Represents player and enemy characters, including health and shiel
shield

## halo_map_parse.py Outline
```python
import struct

def parse_header(file_path):
    with open(file_path, 'rb') as f:
        magic = f.read(4)
        version = struct.unpack('<I', f.read(4))[0]
        tag_index_offset = struct.unpack('<I', f.read(4))[0]
        scenario_tag_index = struct.unpack('<I', f.read(4))[0]
    return {
        'magic': magic,
        'version': version,
        'tag_index_offset': tag_index_offset,
        'scenario_tag_index': scenario_tag_index
    }

def parse_tags(file_path, offset):
    tags = []
    with open(file_path, 'rb') as f:
        f.seek(offset)
        while True:
            tag_id = struct.unpack('<I', f.read(4))[0]
            if not tag_id:
                break
            tag_offset = struct.unpack('<I', f.read(4))[0]
            tags.append((tag_id, tag_offset))
    return tags

def main(file_path):
    header = parse_header(file_path)
    tags = parse_tags(file_path, header['tag_index_offset'])
    for tag in tags:
        print(f"Tag ID: {tag[0]}, Offset: {tag[1]}")

if __name__ == "__main__":
    main('groundhog\\maps\\shared.map')
```

This script parses the .map file header and walks through the tag index to 
list all tags. Adjust the `main` function call with the appropriate .map fi
file path for testing.