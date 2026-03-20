import asyncio
from wizwalker import ClientHandler

async def main():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if clients:
        p = clients[0]
        root = p.root_window
        # We look for any window that has one of the hood names as its text
        hoods = ["karamelle city", "sweetzburg", "nibbleheim", "gutenstadt", "black licorice forest", "candy corn farm", "gobblerton"]
        
        async def scan_for_hood(window, found_hoods=None):
            if found_hoods is None: found_hoods = {}
            try:
                text = await window.maybe_text()
                if text:
                    text_lower = text.lower()
                    for hood in hoods:
                        if hood in text_lower:
                            # Found a potential area name
                            path = []
                            curr = window
                            while curr and curr.name:
                                path.insert(0, curr.name)
                                try:
                                    curr = await curr.parent()
                                except:
                                    break
                            found_hoods[hood] = path
                
                children = await window.children()
                for child in children:
                    await scan_for_hood(child, found_hoods)
            except: pass
            return found_hoods

        print("Scanning UI for hood names...")
        found = await scan_for_hood(root)
        if found:
            for hood, path in found.items():
                print(f"Found {hood} at path: {path}")
        else:
            print("No hood names found in UI tree.")
    else:
        print("No clients found.")

if __name__ == "__main__":
    asyncio.run(main())
