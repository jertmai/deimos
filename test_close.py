import asyncio
from wizwalker import ClientHandler

async def test_close():
    walker = ClientHandler()
    clients = walker.get_new_clients()
    if not clients:
        print("No clients found.")
        return
        
    p = clients[0]
    print(f"Testing close() on {p.title} (PID: {p.process_id})")
    print("This SHOULD detatch without closing the game if it's standard.")
    await p.activate_hooks()
    print("Hooks activated. Now closing client object...")
    await p.close()
    print("Client.close() called. Check if the game is still open!")

if __name__ == "__main__":
    asyncio.run(test_close())
