import asyncio
from wizwalker import ClientHandler

async def main():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if clients:
        p = clients[0]
        try:
            # Check display name of the zone
            zone_dn = await p.zone_display_name()
            print(f"zone_display_name(): {zone_dn}")
        except Exception as e:
            print(f"Error: {e}")
            
        try:
            # Check if there's an area display name
            # Some versions have p.area_display_name()
            if hasattr(p, 'area_display_name'):
                print(f"area_display_name(): {await p.area_display_name()}")
        except: pass

        # Check UI tree for any of the hood names
        hoods = ["nibbleheim", "gutenstadt", "sweetzburg", "karamelle city", "black licorice forest", "candy corn farm", "gobblerton"]
        try:
            # We search for hood names in the text of any UI element
            # This is experimental but might reveal where it is stored
            def search_ui(window, indent=""):
                # This would be too slow over MCP.
                pass
        except: pass

    else:
        print("No clients found.")

if __name__ == "__main__":
    asyncio.run(main())
