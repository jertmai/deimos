import asyncio
from wizwalker import ClientHandler

async def main():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if not clients: return
    p = clients[0]
    hoods = ["nibbleheim", "gutenstadt", "sweetzburg", "karamelle city", "black licorice forest", "candy corn farm", "gobblerton"]
    
    async def find_hood_in_ui(window):
        try:
            text = await window.maybe_text()
            if text:
                text_lower = text.lower()
                for hood in hoods:
                    if hood in text_lower:
                        return hood
            for child in await window.children():
                res = await find_hood_in_ui(child)
                if res: return res
        except: pass
        return None

    print(f"Searching HUD for neighborhood name...")
    res = await find_hood_in_ui(p.root_window)
    if res:
        print(f"FOUND CURRENT NEIGHBORHOOD IN UI: {res}")
    else:
        print("No neighborhood name found in UI.")

if __name__ == "__main__":
    asyncio.run(main())
