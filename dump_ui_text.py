import asyncio
from wizwalker import ClientHandler

async def dump_ui(window, depth=0):
    text = ""
    try:
        # Only check visible windows to save time
        if not await window.is_visible():
            return ""
        
        name = window.name or "Unnamed"
        content = await window.maybe_text()
        if content:
            text += f"{'  ' * depth}[{name}]: {content}\n"
            
        children = await window.children()
        for child in children:
            text += await dump_ui(child, depth + 1)
    except:
        pass
    return text

async def main():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if not clients:
        print("No clients found.")
        return
        
    p = clients[0]
    print(f"Dumping visible UI text for {p}...")
    ui_text = await dump_ui(p.root_window)
    
    with open("ui_dump.txt", "w", encoding="utf-8") as f:
        f.write(ui_text)
    print("Done. Saved to ui_dump.txt")

if __name__ == "__main__":
    asyncio.run(main())
