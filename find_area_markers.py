import asyncio
from wizwalker import ClientHandler

async def main():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if not clients: return
    
    p = clients[0]
    entities = await p.get_base_entity_list()
    print(f"Total entities: {len(entities)}")
    
    for e in entities:
        try:
            template = await e.object_template()
            internal_name = await template.object_name()
            display_name = await p.cache_handler.get_langcode_name(await template.display_name())
            
            # Look for area names
            area_names = ["Nibbleheim", "Gutenstadt", "Sweetzburg", "Black Licorice Forest"]
            for name in area_names:
                if name.lower() in internal_name.lower() or (display_name and name.lower() in display_name.lower()):
                    print(f"FOUND MARKER/ENTITY: {internal_name} (Display: {display_name}) at {await e.location()}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
