import asyncio
import wizwalker
from wizwalker import ClientHandler

async def main():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if clients:
        p = clients[0]
        print(f"Methods on client: {[m for m in dir(p) if 'entity' in m.lower() or 'list' in m.lower()]}")
    else:
        print("No clients found to check.")

if __name__ == "__main__":
    asyncio.run(main())
