import asyncio
from wizwalker import ClientHandler
from loguru import logger

async def debug_scan():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if not clients:
        print("No clients found.")
        return
        
    p = clients[0]
    print(f"--- DEBUG SCAN FOR {p.title} ---")
    
    # Method 1: Active Entity List
    active = await p.get_entity_list()
    print(f"Active Entity List Count: {len(active)}")
    
    # Method 2: Base Entity List (Often has more)
    base = await p.get_base_entity_list()
    print(f"Base Entity List Count: {len(base)}")
    
    # Method 3: Check for specific "Zone" or "World" objects
    # Sometimes entities are attached to the zone manager
    
    all_names = []
    for e in base:
        try:
            template = await e.object_template()
            name = (await template.object_name()).lower()
            all_names.append(name)
            if "chest" in name or "ritual" in name or "cantrip" in name:
                loc = await e.location()
                dist = (await p.body.position()).distance_to(loc)
                print(f"FOUND INTERESTING: {name} at {loc} (Dist: {dist})")
        except:
            pass
            
    # Save a snippet of all names to see what's in memory
    with open("all_entity_names.txt", "w") as f:
        f.write("\n".join(set(all_names)))
    print("Done. Check all_entity_names.txt for the full list of detected names.")

if __name__ == "__main__":
    asyncio.run(debug_scan())
