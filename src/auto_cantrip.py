import asyncio
from loguru import logger
from wizwalker import Client, Keycode
from src.utils import is_free
from src.teleport_math import navmap_tp, calc_Distance

async def cantrip_find_and_move(client: Client):
    try:
        # DEEP MEMORY SWEEP: Collect every possible object in the zone's memory
        entities = []
        try:
            # Source 1: Master Base Pool (Standard registry)
            base_pool = await client.get_base_entity_list()
            # Source 2: Active Entity Manager (Visible objects)
            active_pool = await client.get_entity_list()
            # Source 3: Attempt a vague name search which sometimes populates culled objects
            ritual_sites = await client.get_base_entities_with_name("Ritual")
            
            seen_ids = set()
            for e in (base_pool + active_pool + ritual_sites):
                try:
                    gid = await e.global_id_full()
                    if gid not in seen_ids:
                        entities.append(e)
                        seen_ids.add(gid)
                except: pass
        except:
            entities = await client.get_base_entity_list()
            
        if not entities:
            return

        # Neighborhood Logic (For Karamelle Hubs)
        neighborhood_markers = ["nibbleheim", "gutenstadt", "sweetzburg", "karamelle city", "black licorice forest", "candy corn farm", "gobblerton", "rock candy mount"]
        found_markers = []
        for e in entities:
            try:
                template = await e.object_template()
                int_name = (await template.object_name()).lower()
                for hood in neighborhood_markers:
                    if hood in int_name:
                        found_markers.append({'xyz': await e.location(), 'name': hood})
                        break
            except: pass

        curr_pos = await client.body.position()
        current_hood = None
        if len(set(m['name'] for m in found_markers)) > 1:
            found_markers.sort(key=lambda m: calc_Distance(curr_pos, m['xyz']))
            current_hood = found_markers[0]['name']

        possible_targets = []
        # Support both Husk and Karamelle naming styles
        target_words = ["cantrip", "ritual"]
        
        for e in entities:
            try:
                found_match = False
                match_name = ""
                template = await e.object_template()
                internal_name = (await template.object_name()).lower()
                
                # Broad Match: Must contain ritual/cantrip AND chest/prop
                if any(word in internal_name for word in target_words) and ("chest" in internal_name or "prop" in internal_name or "shrine" in internal_name):
                    found_match = True
                    match_name = internal_name
                
                if not found_match:
                    try:
                        dn_code = await template.display_name()
                        display_name = (await client.cache_handler.get_langcode_name(dn_code)).lower()
                        if any(word in display_name for word in target_words) and "chest" in display_name:
                            found_match = True
                            match_name = display_name
                    except: pass

                if found_match:
                    if any(bad in match_name for bad in ["player", "mount", "npc", "pet", "friend"]):
                        continue
                        
                    chest_loc = await e.location()
                    
                    if current_hood:
                        chest_markers = sorted(found_markers, key=lambda m: calc_Distance(chest_loc, m['xyz']))
                        if chest_markers[0]['name'] != current_hood:
                            continue

                    dist = calc_Distance(curr_pos, chest_loc)
                    possible_targets.append({'xyz': chest_loc, 'name': match_name, 'dist': dist})
            except: continue

        if not possible_targets:
            return

        # Target closest valid site
        possible_targets.sort(key=lambda x: x['dist'])
        target = possible_targets[0]
        
        # Wait for character to be free before porting
        if not await is_free(client) or getattr(client, 'entity_detect_combat_status', False):
            return

        # BLINK PORT
        logger.info(f"[{client.title}] DETECTED {target['name']} at {int(target['dist'])} units. Teleporting...")
        await navmap_tp(client, target['xyz'])
        
        # Interaction Loop
        for attempt in range(3):
            await asyncio.sleep(0.3)
            logger.success(f"[{client.title}] Interaction attempt {attempt+1}")
            await client.send_key(Keycode.X, 0.1)
            await asyncio.sleep(0.5)
            
        await asyncio.sleep(1.0)
            
    except Exception as e:
        logger.error(f"Error in cantrip_hunt for {client.title}: {e}")

async def auto_cantrip_loop(clients: list[Client], debug: bool = True):
    try:
        logger.info("Universal Area Cantrip Hunt active. Scanning full zone...")
        while True:
            for c in clients:
                # Persistent loop: continues until user disables cantrip_status
                if getattr(c, 'cantrip_status', False) and not getattr(c, '_cantrip_hunting', False):
                    c._cantrip_hunting = True
                    asyncio.create_task(cantrip_check_wrapper(c))
            
            # Responsive re-scan interval
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        logger.info("Cantrip Hunt deactivated.")

async def cantrip_check_wrapper(client: Client):
    try:
        await cantrip_find_and_move(client)
    finally:
        client._cantrip_hunting = False
