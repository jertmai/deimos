import asyncio
from wizwalker import ClientHandler

async def main():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if not clients: return
    p = clients[0]
    try:
        print(f"zone_name(): {await p.zone_name()}")
        print(f"zone_display_name(): {await p.zone_display_name()}")
        # Check for any other attributes
        for attr in ['area_name', 'subzone_name', 'area_display_name']:
            if hasattr(p, attr):
                try:
                    val = await getattr(p, attr)() if callable(getattr(p, attr)) else getattr(p, attr)
                    print(f"{attr}: {val}")
                except: pass
    except: pass

if __name__ == "__main__":
    asyncio.run(main())
