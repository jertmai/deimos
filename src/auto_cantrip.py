import math
import asyncio
from loguru import logger
from wizwalker import Keycode, XYZ
from wizwalker.client_handler import Client
from src.paths import open_cantrips_path
from src.utils import is_free, click_window_by_path
from src.teleport_math import navmap_tp, calc_Distance, calculate_yaw

# Global session cache to prevent double-casting on the same site
completed_sites = set()

async def cantrip_find_and_move(client: Client):
    try:
        # EXTREME RANGE OVERRIDE: Unlock 20,000 unit detection horizon
        try:
            if hasattr(client, 'entity_manager'):
                client.entity_manager.detect_range = 20000.0
        except: pass

        # ABSOLUTE ZONE RADAR: Memory sweep for all ritual variants
        entities = []
        try:
            # We use every available registry to ensure no object is missed at distance
            base_pool = await client.get_base_entity_list()
            v_ritual = await client.get_base_entities_with_vague_name("Ritual")
            v_cantrip = await client.get_base_entities_with_vague_name("Cantrip")
            active_pool = await client.get_entity_list()
            
            aggregator = base_pool + v_ritual + v_cantrip + active_pool
            seen_ids = set()
            for e in aggregator:
                try:
                    gid = await e.global_id_full()
                    # Skip sites we've already cast on in this session, and duplicates
                    if gid not in seen_ids and gid not in completed_sites:
                        entities.append(e)
                        seen_ids.add(gid)
                except: pass
        except:
            entities = await client.get_base_entity_list()
            
        if not entities:
            return

        # District Identification (Handles multi-neighborhood hubs)
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
        # Neighborhood grouping is only active in dense urban hubs
        if len(set(m['name'] for m in found_markers)) > 1:
            found_markers.sort(key=lambda m: calc_Distance(curr_pos, m['xyz']))
            current_hood = found_markers[0]['name']

        possible_targets = []
        target_words = ["cantrip", "ritual"]
        interact_types = ["chest", "prop", "shrine", "site", "node", "altar", "spot"]
        
        valid_entity = None
        for e in entities:
            try:
                found_match = False
                match_name = ""
                template = await e.object_template()
                internal_name = (await template.object_name()).lower()
                
                if any(word in internal_name for word in target_words) and any(it in internal_name for it in interact_types):
                    found_match = True
                    match_name = internal_name
                
                if not found_match:
                    try:
                        dn_code = await template.display_name()
                        display_name = (await client.cache_handler.get_langcode_name(dn_code)).lower()
                        if any(word in display_name for word in target_words) and any(it in display_name for it in interact_types):
                            found_match = True
                            match_name = display_name
                    except: pass

                if found_match:
                    # Ignore non-chest entities
                    if any(bad in match_name for bad in ["player", "mount", "npc", "pet", "friend", "enemy"]):
                        continue
                        
                    chest_loc = await e.location()
                    
                    # Filter by neighborhood only if we are in a Hub
                    if current_hood:
                        chest_markers = sorted(found_markers, key=lambda m: calc_Distance(chest_loc, m['xyz']))
                        if chest_markers[0]['name'] != current_hood:
                            continue

                    dist = calc_Distance(curr_pos, chest_loc)
                    gid = await e.global_id_full()
                    # Radar now officially accepts targets up to 20,000+ units away
                    possible_targets.append({'xyz': chest_loc, 'name': match_name, 'dist': dist, 'entity': e, 'gid': gid})
            except: continue

        if not possible_targets:
            return

        # Closest Site First
        possible_targets.sort(key=lambda x: x['dist'])
        target = possible_targets[0]
        target_entity = target['entity']
        target_xyz = target['xyz']
        target_gid = target['gid']
        
        # Free-state Check
        if not await is_free(client) or getattr(client, 'entity_detect_combat_status', False):
            return

        # STRAIGHT-ON POSITIONING
        # We read the chest's own rotation to find where its 'front' is
        try:
            target_yaw = await target_entity.body.yaw()
        except:
            target_yaw = 0.0
            
        stand_back_dist = 90.0
        # Teleport to the exact standoff position calculated from the chest's rotation
        arrival_x = target_xyz.x - (stand_back_dist * math.sin(target_yaw))
        arrival_y = target_xyz.y - (stand_back_dist * math.cos(target_yaw))
        arrival_z = target_xyz.z
        arrival_xyz = XYZ(arrival_x, arrival_y, arrival_z)

        # Blink Port
        logger.info(f"[{client.title}] RADAR: Moving to {target['name']} ({int(target['dist'])} units)...")
        await navmap_tp(client, arrival_xyz)
        await asyncio.sleep(0.4)
        
        # ROTATION: Face chest
        try:
            face_yaw = calculate_yaw(arrival_xyz, target_xyz)
            await client.body.write_yaw(face_yaw)
        except: pass

        # 1. CLICK WAND ICON (Above Backpack)
        logger.debug(f"[{client.title}] Opening Cantrip Menu...")
        try:
            await click_window_by_path(client, open_cantrips_path)
            await asyncio.sleep(0.7)
            
            # 2. CLICK MAGIC TOUCH SPELL
            mt_buttons = await client.root_window.get_windows_with_text("Magic Touch")
            if not mt_buttons:
                mt_buttons = await client.root_window.get_windows_with_name("MagicTouch")
            
            if mt_buttons:
                await mt_buttons[0].click()
                await asyncio.sleep(0.5)
                logger.success(f"[{client.title}] Magic Touch Selected")
            else:
                logger.warning(f"[{client.title}] Magic Touch not found. Brute force X.")
                await client.send_key(Keycode.X, 0.1)
                # Still mark as completed so we don't get stuck on it
                completed_sites.add(target_gid)
                return 

            # 3. CLICK CENTER OF THE CHEST (World-to-Screen)
            # Position alignment is now 'straight' so center-click is perfect
            screen_pos = await client.world_to_screen(target_xyz)
            if screen_pos:
                logger.info(f"[{client.title}] Casting Magic Touch on {target['name']}")
                # MARK SITE AS COMPLETED: So we don't cast on it twice
                completed_sites.add(target_gid)
                await client.mouse.click(screen_pos.x, screen_pos.y)
                await asyncio.sleep(1.0)
                
        except Exception as proc_err:
            logger.error(f"[{client.title}] Interaction failed: {proc_err}")

        # Rapid handover to next chest
        await asyncio.sleep(0.5)
            
    except Exception as e:
        logger.error(f"Error in cantrip_hunt for {client.title}: {e}")

async def auto_cantrip_loop(clients: list[Client], debug: bool = True):
    try:
        logger.info("Universal Chain Cantrip Hunt active. Scanning for sites...")
        while True:
            for c in clients:
                if getattr(c, 'cantrip_status', False) and not getattr(c, '_cantrip_hunting', False):
                    c._cantrip_hunting = True
                    asyncio.create_task(cantrip_check_wrapper(c))
            
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        logger.info("Cantrip Hunt deactivated.")

async def cantrip_check_wrapper(client: Client):
    try:
        await cantrip_find_and_move(client)
    finally:
        client._cantrip_hunting = False
