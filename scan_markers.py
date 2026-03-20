import asyncio
from wizwalker import ClientHandler

async def main():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if not clients: return
    
    p = clients[0]
    entities = await p.get_base_entity_list()
    print(f"Total entities: {len(entities)}")
    
    found_any = False
    for e in entities:
        try:
            template = await e.object_template()
            internal_name = await template.object_name()
            # print(f"Checking {internal_name}") # Too much output
            
            # Area markers are often named "Entrance", "Marker", "Zone", "Area", "Prop_Signpost"
            keywords = ["marker", "entrance", "zone", "signpost", "teleport"]
            if any(k in internal_name.lower() for k in keywords):
                # Only print interesting ones
                display_name = await p.cache_handler.get_langcode_name(await template.display_name())
                if display_name:
                    print(f"INTERESTING: {internal_name} - DISPLAY: {display_name} - LOC: {await e.location()}")
                    found_any = True
        except:
            pass
    if not found_any:
        print("No interesting area markers found.")

if __name__ == "__main__":
    asyncio.run(main())
