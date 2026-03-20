import asyncio
import wizwalker
from wizwalker import ClientHandler

async def main():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if clients:
        p = clients[0]
        # Check client methods/properties related to zone/area
        zone_methods = [m for m in dir(p) if 'zone' in m.lower() or 'area' in m.lower() or 'location' in m.lower()]
        print(f"Zone methods: {zone_methods}")
        
        # Try some common calls
        try:
            print(f"zone_name(): {await p.zone_name()}")
        except Exception as e:
            print(f"Error calling zone_name: {e}")
            
        try:
            # Some wizwalker versions have area_name or similar
            if hasattr(p, 'area_name'):
                print(f"area_name(): {await p.area_name()}")
        except: pass

        # Check subzones if possible
        try:
            if hasattr(p, 'subzone_name'):
                print(f"subzone_name(): {await p.subzone_name()}")
        except: pass

        # Check HUD for current area name
        # Often it is in a window named 'ZoneLabel' or 'AreaLabel'
        try:
            root = p.root_window
            # Deep search for area names
            area_names = ["Nibbleheim", "Gutenstadt", "Karamelle", "Sweetzburg"]
            for name in area_names:
                found = await root.find_child_with_name(name, recursive=True)
                if found:
                    print(f"Found UI element with name {name}")
                
                # Check text content
                # This is harder without a specific path, but let's try some common HUD children
                hud = await root.find_child_with_name("windowHUD", recursive=True)
                if hud:
                    # Search text in HUD
                    # (This is slow, so we only do it for one client)
                    pass

        except: pass

    else:
        print("No clients found.")

if __name__ == "__main__":
    asyncio.run(main())
