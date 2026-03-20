import asyncio
from typing import List, Optional, Tuple

from src.smart_combat import SmartCombat
from src.effect_simulation import sim_damage, sim_heal, sim_effect, MagicSchoolID
from wizwalker.memory.memory_objects.enums import MagicSchool
from src.combat_cache import cache_get
from wizwalker.extensions.wizsprinter.sprinty_combat import does_card_contain_reqs, SpellType
from wizwalker.extensions.wizsprinter.combat_backends.combat_api import MoveConfig, Move, TargetData, TargetType, NamedSpell, TemplateSpell
import wizwalker.errors
from src.utils import class_snapshot, is_control_grayed, click_window_by_path, is_visible_by_path
from loguru import logger
from src.paths import deck_config_tc_tab_path, deck_config_sun_filter_path, deck_config_tc_list_path, close_spellbook_path

class AICombat(SmartCombat):
    def __init__(self, client, config_provider, handle_mouseless=False, pre55_mode=False):
        super().__init__(client, config_provider, handle_mouseless)
        self.pre55_mode = pre55_mode
        self.ai_mode = True
        self.min_heal_threshold = 0.4  # Heal if below 40% HP
        self.kill_threshold = 1.0  # Damage needed to kill
        
        # Action tracking (to prevent redundant buffing)
        self.cast_aura = False
        self.cast_feint = False
        self.cast_trap = False
        self.cast_prism = False
        self.hammer_name = None
        self.side_deck_path = ['WorldView', 'PlanningPhase', 'Alignment', 'PlanningPhaseSubWindow', 'SpellSelection', 'DrawButton']
        self.side_deck_empty = False

    async def clean_hand(self) -> bool:
        """Advanced hand cleaning for AI combat: discards contextual 'trash' to cycle cards."""
        made_action = await super().clean_hand()
        if made_action:
            return True

        cards = await self.get_cards()
        if not cards:
            return False

        # Templates for identification
        template_blade = TemplateSpell([SpellType.type_blade], False)
        template_heal = TemplateSpell([SpellType.type_heal], False)
        template_aoe = TemplateSpell([SpellType.type_aoe], False)
        template_aura = TemplateSpell([SpellType.type_aura], False)
        template_global = TemplateSpell([SpellType.type_global], False)
        template_enchant = TemplateSpell([SpellType.type_enchant], False)
        template_damage = TemplateSpell([SpellType.type_damage], False)

        boss = await self.get_alive_boss()
        client_member = await self.get_client_member()
        client_snap = await class_snapshot(client_member)
        wiz_level = client_snap.get("level", 1)

        # --- RULE #5: AGGRESSIVE WAND DISCARDING ---
        # Wand hits (0-pip spells) are just clutter. Discard them immediately to cycle.
        for card in cards:
            is_attack = await does_card_contain_reqs(card, template_damage) or await does_card_contain_reqs(card, template_aoe)
            if is_attack:
                snap = await class_snapshot(card)
                if snap.get("get_pip_cost", 0) == 0:
                    logger.debug(f"AI Combat: Discarding weak wand hit to cycle: {await card.name()}")
                    await card.discard(sleep_time=0.2)
                    return True

        # --- RULE #6: PRE-55 ENCHANT FISHING ---
        # If we have hits but no enchant, we MUST find one in the side deck.
        if self.pre55_mode or (wiz_level is not None and wiz_level < 55):
            has_hit = any(await does_card_contain_reqs(c, template_damage) or await does_card_contain_reqs(c, template_aoe) for c in cards)
            has_enchant = any(await does_card_contain_reqs(c, template_enchant) for c in cards)

            if has_hit and not has_enchant:
                # Check side deck state
                button_control = await self.client.root_window.get_window_by_path(self.side_deck_path)
                if button_control and await is_control_grayed(button_control):
                    self.side_deck_empty = True
                else:
                    # Discard literally anything that isn't a hit or a blade
                    for card in cards:
                        is_hit = await does_card_contain_reqs(card, template_damage) or await does_card_contain_reqs(card, template_aoe)
                        is_blade = await does_card_contain_reqs(card, template_blade)
                        if not is_hit and not is_blade:
                            logger.debug(f"AI Combat: Discarding {await card.name()} to FISH for side-deck Enchant.")
                            await card.discard(sleep_time=0.2)
                            await self.draw_tc()
                            return True

        # General "Lazy" protection: if hand is too small, stop here.
        if len(cards) < 3:
            return False

        health = client_snap.get("health", 0)
        max_health = client_snap.get("max_health", 1)
        if health is None: health = 0
        if max_health is None or max_health == 0: max_health = 1
        hp_percent = health / max_health

        discard_candidate = None

        # 1. Discard heals if we are healthy and hand is getting full
        if hp_percent > 0.8:
            for card in cards:
                if await does_card_contain_reqs(card, template_heal):
                    discard_candidate = card
                    break

        # 2. Discard redundant Auras/Globals
        if not discard_candidate:
            for card in cards:
                if await does_card_contain_reqs(card, template_aura) and self.cast_aura:
                    discard_candidate = card
                    break
        
        # 3. Discard AOEs in single-target boss fights if we have better options
        if not discard_candidate and boss and len(await self.get_enemies()) == 1:
            for card in cards:
                if await does_card_contain_reqs(card, template_aoe):
                    # Only discard if we have at least 1 other attack or if hand is very full
                    discard_candidate = card
                    break
        
        # 4. Handle "Enchant Overload" (Too many enchants, no hits)
        if not discard_candidate:
            enchants = [c for c in cards if await does_card_contain_reqs(c, template_enchant)]
            hits = [c for c in cards if await does_card_contain_reqs(c, template_aoe) or await does_card_contain_reqs(c, template_damage)]
            if len(enchants) > 2 and not hits:
                # We are stuck with enchants but nothing to use them on. Discard the lowest value one (heuristic: first found)
                discard_candidate = enchants[0]

        # 5. Pre-level 55 Side-Deck Enchant Strategy
        # If we have hits but no enchant, discard trash and draw from TC deck
        wiz_level = client_snap.get("level", 1)
        if self.pre55_mode or (wiz_level is not None and wiz_level < 55):
            has_hit = any(await does_card_contain_reqs(c, template_damage) or await does_card_contain_reqs(c, template_aoe) for c in cards)
            has_enchant = any(await does_card_contain_reqs(c, template_enchant) for c in cards)

            if has_hit and not has_enchant:
                # Check if side deck is actually empty BEFORE we discard something!
                button_control = await self.client.root_window.get_window_by_path(self.side_deck_path)
                if button_control and await is_control_grayed(button_control):
                    if not self.side_deck_empty:
                        logger.warning("AI Combat: Side Deck is empty! Stopping TC draw attempts.")
                        self.side_deck_empty = True
                else:
                    # Find something truly useless to discard for a TC draw
                    for card in cards:
                        is_hit = await does_card_contain_reqs(card, template_damage) or await does_card_contain_reqs(card, template_aoe)
                        is_blade = await does_card_contain_reqs(card, template_blade)
                        is_utility = await does_card_contain_reqs(card, template_aura) or await does_card_contain_reqs(card, template_global)
                        
                        # If it's not a hit and we have duplicates or it's a generic utility we don't need right now
                        if not is_hit and not is_blade:
                            logger.debug(f"AI Combat: Discarding {await card.name()} to DRAW Enchant TC.")
                            await card.discard(sleep_time=0.2)
                            await self.draw_tc()
                            return True

        # 6. Mob Battle Cleanup (Discard Traps/Feints/Prisms)
        if not boss:
            template_trap = TemplateSpell([SpellType.type_trap], False)
            template_prism = TemplateSpell([SpellType.type_prism], False)
            for card in cards:
                c_name = (await card.name()).lower()
                is_trap = await does_card_contain_reqs(card, template_trap)
                is_prism = await does_card_contain_reqs(card, template_prism)
                is_feint = "feint" in c_name
                
                if is_trap or is_prism or is_feint:
                    logger.debug(f"AI Combat: Mob battle detected. Discarding useless utility: {c_name}")
                    await card.discard(sleep_time=0.2)
                    return True

        # --- RULE #7: BRUTAL CYCLING (Loop to discard everything useless) ---
        did_discard_multi = False
        deck_count = client_snap.get("get_participant", {}).get("get_deck_count", 30)

        while True: # Keep discarding until clean
            cards = await self.get_cards()
            if len(cards) < 2: break
            
            current_discard = None
            has_hit = any(await does_card_contain_reqs(c, template_damage) or await does_card_contain_reqs(c, template_aoe) for c in cards)
            has_enchant = any(await does_card_contain_reqs(c, template_enchant) for c in cards)
            
            # Identify junk
            seen_names = set()
            for card in cards:
                c_name = await card.name()
                is_strike = await does_card_contain_reqs(card, template_damage) or await does_card_contain_reqs(card, template_aoe)
                is_blade = await does_card_contain_reqs(card, template_blade)
                is_enchant = await does_card_contain_reqs(card, template_enchant)
                
                # Rule #5: Wand Hits (0-pip clutter)
                if is_strike:
                    snap = await class_snapshot(card)
                    if snap.get("get_pip_cost", 0) == 0:
                        current_discard = card
                        break

                # Rule #1: Duplicate non-strikes
                if not is_strike and c_name in seen_names:
                    current_discard = card
                    break
                seen_names.add(c_name)
                
                # Rule #6: Pre-55 mode cleanup (Anything not hit/blade/enchant)
                if (self.pre55_mode or (wiz_level is not None and wiz_level < 55)) and not (is_strike or is_blade or is_enchant):
                    current_discard = card
                    break
                
                # Rule #4: Fish for Reshuffle if deck is low
                if not self.pre55_mode and wiz_level >= 55 and deck_count < 7:
                    if not (is_strike or is_blade or "reshuffle" in c_name.lower()):
                        current_discard = card
                        break

            if current_discard:
                logger.debug(f"AI Combat: Brutal Cycle - Discarding {await current_discard.name()} to refresh hand.")
                await current_discard.discard(sleep_time=0.1)
                did_discard_multi = True
            else:
                break
        
        if did_discard_multi:
            # Re-fetch cards to check enchant state again
            cards = await self.get_cards()
            has_enchant = any(await does_card_contain_reqs(c, template_enchant) for c in cards)
            if (self.pre55_mode or (wiz_level is not None and wiz_level < 55)) and not has_enchant:
                await self.draw_tc()
            return True

        return False

    async def draw_tc(self):
        """Draws a card from the side deck (TC deck), with empty detection."""
        logger.debug("AI Combat: Checking Side Deck state.")
        
        button_control = await self.client.root_window.get_window_by_path(self.side_deck_path)
        if button_control and await is_control_grayed(button_control):
            logger.warning("AI Combat: Side Deck is EMPTY!")
            self.side_deck_empty = True
            return

        logger.debug("AI Combat: Drawing from Side Deck (TC).")
        await click_window_by_path(self.client, self.side_deck_path, hooks=True)
        await asyncio.sleep(0.5)

    async def refill_side_deck(self):
        """Opens the spellbook and refills the side deck with Sun enchants."""
        if await self.client.in_battle():
            logger.warning("AI Combat: Cannot refill side deck while in combat!")
            return

        logger.info(f"AI Combat: Refilling side deck for {self.client.title}...")
        
        # 1. Open Spellbook
        await self.client.send_key(wizwalker.Keycode.P, 0.2)
        await asyncio.sleep(1.5) # Wait for UI
        
        if not await is_visible_by_path(self.client, deck_config_tc_tab_path):
            logger.error("AI Combat: Failed to open Deck Configuration.")
            return

        # 2. Go to TC Tab
        await click_window_by_path(self.client, deck_config_tc_tab_path)
        await asyncio.sleep(0.5)
        
        # 3. Click Sun Filter (Astral)
        await click_window_by_path(self.client, deck_config_sun_filter_path)
        await asyncio.sleep(0.8)

        # 4. Find and Add Damage Enchants
        # Iterate through all cards in the TC window and look for enchants
        tc_list_window = await self.client.root_window.get_window_by_path(deck_config_tc_list_path)
        if tc_list_window:
            enchants_to_find = ["tough", "strong", "giant", "monstrous", "gargantuan", "colossal", "epic"]
            children = await tc_list_window.children()
            
            logger.debug(f"AI Combat: Scanning {len(children)} TC slots for enchants...")
            for child in children:
                # Some children might be scrollbars or spacers, skip them
                try:
                    c_name = (await child.object_name()).lower()
                    # If we can't get card name directly, we might need a child text element
                    # For now, we assume the object name or a text child contains the name
                    card_title = c_name
                    
                    # Search for any known enchant name in the card's name
                    if any(enc in card_title for enc in enchants_to_find):
                        logger.info(f"AI Combat: Found enchant {card_title}. Adding to side deck.")
                        # Right click multiple times to fill up
                        for _ in range(15):
                            await self.client.mouse_handler.right_click_window(child)
                            await asyncio.sleep(0.02)
                except:
                    continue
        else:
            logger.error("AI Combat: TC List window (wndTCList) not found.")
        
        # 5. Close Spellbook
        await click_window_by_path(self.client, close_spellbook_path)
        logger.info("AI Combat: Side deck refill complete.")
        self.side_deck_empty = False

    async def get_duel_snapshot(self):
        """Creates a snapshot of the current duel state for simulation."""
        duel = await class_snapshot(self.client.duel)
        members = await self.get_members()
        member_snapshots = [await class_snapshot(m) for m in members]
        
        # Identify teams
        client_member = await self.get_client_member()
        client_snapshot = await class_snapshot(client_member)
        team_id = cache_get(client_snapshot, "get_participant.team_id")
        
        allies = [m for m in member_snapshots if cache_get(m, "get_participant.team_id") == team_id]
        enemies = [m for m in member_snapshots if cache_get(m, "get_participant.team_id") != team_id]
        
        # 1. Identify "The Hammer" (Wizard with highest damage stats)
        max_dmg = -1
        hammer = None
        for ally in allies:
            # We check the generic damage bonus as a heuristic for who the carry is
            dmg = cache_get(ally, "get_stats.dmg_bonus_percent_all")
            if dmg is None:
                dmg = 0.0
            if dmg > max_dmg:
                max_dmg = dmg
                hammer = ally
        
        self.hammer_name = hammer.get("name") if hammer else None
        
        return duel, client_snapshot, allies, enemies, hammer

    async def score_move(self, move_config: MoveConfig, duel_snap, client_snap, allies_snap, enemies_snap) -> float:
        """Scores a move based on simulated outcome."""
        # This is a simplified scoring system.
        # In a full implementation, we'd simulate the effect of the spell.
        
        # For now, let's use heuristics based on the simulation logic.
        score = 0.0
        
        health = client_snap.get("health", 0)
        max_health = client_snap.get("max_health", 1)
        if health is None: health = 0
        if max_health is None or max_health == 0: max_health = 1
        hp_percent = health / max_health

        # 1. Healing Score
        if "heal" in str(move_config.move.card).lower() or (isinstance(move_config.move.card, TemplateSpell) and SpellType.type_heal in move_config.move.card.requirements):
            if hp_percent < self.min_heal_threshold:
                score = (1.0 - hp_percent) * 10  # High priority if low HP
        
        # 2. Damage Score & Kill-Shot detection
        if "damage" in str(move_config.move.card).lower() or (isinstance(move_config.move.card, TemplateSpell) and (SpellType.type_damage in move_config.move.card.spell_types or SpellType.type_aoe in move_config.move.card.spell_types)):
            # If we were doing a full sim, we'd call sim_damage here.
            # Simplified: If the target is at low HP, give it a boost.
            target_hp = enemies_snap[0].get("health", 10000) if (enemies_snap and enemies_snap[0]) else 10000
            if target_hp is None: target_hp = 10000
            if target_hp < 500: # Heuristic for low health
                score = 5.0
        
        return score

    async def check_kill_shot(self, duel_snap, client_snap, enemies_snap) -> Optional[MoveConfig]:
        """Simulates all available attacks to see if we can win the fight this turn."""
        cards = await self.get_cards()
        template_damage = TemplateSpell([SpellType.type_damage], False)
        template_aoe = TemplateSpell([SpellType.type_aoe], False)
        template_enchant = TemplateSpell([SpellType.type_enchant], False)
        
        # Check if we actually HAVE an enchant in hand
        has_enchant = any(await does_card_contain_reqs(c, template_enchant) for c in cards)
        wiz_level = client_snap.get("level", 1)
        
        attacks = [c for c in cards if await does_card_contain_reqs(c, template_damage) or await does_card_contain_reqs(c, template_aoe)]
        if not attacks:
            return None
            
        best_kill = None
        min_pips = 99
        
        for enemy in enemies_snap:
            enemy_hp = enemy.get("health", 0)
            if enemy_hp is None or enemy_hp <= 0: continue
            
            for attack in attacks:
                # Get pip cost for efficiency check
                try:
                    card_snap = await class_snapshot(attack)
                    pip_cost = card_snap.get("get_pip_cost", 0) or 0
                except:
                    pip_cost = 0

                # Estimate base damage based on level
                if wiz_level < 30:
                    base_dmg = 250 
                elif wiz_level < 55:
                    base_dmg = 450 
                else:
                    base_dmg = 800 
                
                if wiz_level >= 55 or has_enchant:
                    base_dmg += 200 
                
                dmg_bonus = cache_get(client_snap, "get_stats.dmg_bonus_percent_all") or 0.0
                est_dmg = base_dmg * (1 + dmg_bonus)
                
                if est_dmg >= enemy_hp:
                    # Logic: We want the Kills that use the FEWEST pips
                    if pip_cost < min_pips:
                        min_pips = pip_cost
                        logger.debug(f"AI Combat: Found potential Kill-Shot ({int(est_dmg)} dmg) with {await attack.name()}. Pips: {pip_cost}")
                        target = TargetData(TargetType.type_named, await enemy["_original"].name(), True)
                        enchant_to_use = template_enchant if (wiz_level >= 15 or has_enchant) else None
                        best_kill = MoveConfig(Move(attack, enchant=enchant_to_use), target=target)
        
        return best_kill

    async def get_dynamic_priorities(self) -> list[MoveConfig]:
        """Overrides priority logic with AI-driven decisions."""
        boss = await self.get_alive_boss()
        self.boss_mode = (boss is not None)
        
        # Get snapshots for simulation
        try:
            duel_snap, client_snap, allies_snap, enemies_snap, hammer_snap = await self.get_duel_snapshot()
        except Exception as e:
            logger.error(f"AI Combat snapshot failed: {e}")
            return await super().get_dynamic_priorities()

        priorities = []
        
        # 0. KILL-SHOT (Damage Prediction)
        kill_move = await self.check_kill_shot(duel_snap, client_snap, enemies_snap)
        if kill_move:
            priorities.append(kill_move)
        
        # Templates
        template_blade = TemplateSpell([SpellType.type_blade], False)
        template_trap = TemplateSpell([SpellType.type_trap], False)
        template_aura = TemplateSpell([SpellType.type_aura], False)
        template_damage = TemplateSpell([SpellType.type_damage], False)
        template_aoe = TemplateSpell([SpellType.type_aoe], False)
        template_enchant = TemplateSpell([SpellType.type_enchant], False)
        template_heal = TemplateSpell([SpellType.type_heal], False)
        template_cleanse = NamedSpell("Cleanse Charm", False) # Cheat Protection
        template_prism = TemplateSpell([SpellType.type_prism], False)
        template_bubble = TemplateSpell([SpellType.type_global], False)

        # 1. EMERGENCY HEAL / CLEANSE (Cheat Protection)
        health = client_snap.get("health", 0)
        max_health = client_snap.get("max_health", 1)
        if health is None: health = 0
        if max_health is None or max_health == 0: max_health = 1
        hp_percent = health / max_health
        
        # Check for harmful debuffs (Weakness/Infection) - Part of Cheat Protection
        has_weakness = any("weakness" in str(e).lower() for e in cache_get(client_snap, "get_participant.hanging_effects"))
        if has_weakness:
            logger.debug("AI Combat: Cheat/Debuff detected (Weakness). Prioritizing Cleanse.")
            priorities.append(MoveConfig(Move(template_cleanse), target=TargetData(TargetType.type_self)))

        if hp_percent < self.min_heal_threshold:
            logger.debug(f"AI Combat: HP at {hp_percent:.1%}. Prioritizing healing.")
            # Priority 1: Self heal, Priority 2: Group heal (if self heal not found)
            priorities.append(MoveConfig(Move(template_heal), target=TargetData(TargetType.type_self)))
            protocol_group_heal = TemplateSpell([SpellType.type_heal], True) # AOE heal
            priorities.append(MoveConfig(Move(protocol_group_heal)))

        # 2. PRISM (School Contrast - BOSS ONLY)
        if self.boss_mode:
            my_school = client_snap.get("get_stats", {}).get("primary_school", MagicSchool.balance.value)
            for enemy in await self.get_enemies():
                if not await enemy.is_dead():
                    enemy_snap = await class_snapshot(enemy)
                    enemy_school = cache_get(enemy_snap, "get_stats.primary_school")
                    
                    if enemy_school == my_school:
                        if not self.cast_prism:
                            priorities.append(MoveConfig(Move(template_prism), target=TargetData(TargetType.type_named, await enemy.name(), True)))

        priorities.append(MoveConfig(Move(template_bubble)))
        
        # --- NEW AGGRESSIVE BATTLE LOGIC ---
        # 4. SINGLE BLADE (Primary Hammer/Self)
        # We only blade ONCE before going for the hit
        is_bladed = any("blade" in str(e).lower() for e in cache_get(client_snap, "get_participant.hanging_effects"))
        if not is_bladed:
            blade_target = TargetData(TargetType.type_self)
            if self.hammer_name and self.hammer_name != await self.client.name():
                blade_target = TargetData(TargetType.type_named, self.hammer_name, False)
            priorities.append(MoveConfig(Move(template_blade), target=blade_target))

        # 5. ATTACK (Enchanted) - High priority after 1 blade
        # If blade is up OR we don't have one, go straight for the hit
        alive_enemies = [e for e in await self.get_enemies() if not await e.is_dead()]
        mobs = [e for e in alive_enemies if not await e.is_boss()]
        kill_minions_first = getattr(self.client, 'kill_minions_first', False)

        # 5a. AOE Attack
        if len(mobs) > 1 or (not self.boss_mode and alive_enemies):
            priorities.append(MoveConfig(Move(template_aoe, enchant=template_enchant)))
            priorities.append(MoveConfig(Move(template_aoe)))

        # 5b. Single Target Attacks
        priorities.append(MoveConfig(Move(template_damage, enchant=template_enchant), target=TargetData(TargetType.type_enemy)))
        priorities.append(MoveConfig(Move(template_damage), target=TargetData(TargetType.type_enemy)))

        # 6. BOSS DEBUFFING (If no hit available)
        if self.boss_mode:
            boss_target = TargetData(TargetType.type_named, await boss.name(), True)
            
            # If mobs are still alive, we only Feint if we are in 'Minion First' mode or have enough health
            # Otherwise, we might save the pips for an AOE
            should_debuff_boss = not mobs or not kill_minions_first
            
            if should_debuff_boss:
                if not self.cast_feint:
                    priorities.append(MoveConfig(Move(NamedSpell("Feint", False)), target=boss_target))
                if not self.cast_trap:
                    priorities.append(MoveConfig(Move(template_trap), target=boss_target))
        
        # 7. PASSIVE SUPPORT (If nothing else can be done)
        # Standard boss/enemy hits already added above

        # 8. PASS (Explicitly build pips if no priority action is taken)
        # By adding this to the end of the list, we ensure the bot passes 
        # instead of accidentally casting something low-value if no other moves match.
        priorities.append(MoveConfig(Move(NamedSpell("pass", True))))

        return priorities

    async def try_execute_config(self, move_config: MoveConfig) -> bool:
        """Overrides execution to track state flags for AI decision making."""
        success = await super().try_execute_config(move_config)
        if success:
            card = move_config.move.card
            # Update tracking flags based on what we just cast
            if isinstance(card, TemplateSpell):
                if SpellType.type_aura in card.requirements or SpellType.type_global in card.requirements:
                    self.cast_aura = True
                if SpellType.type_prism in card.requirements:
                    self.cast_prism = True
                if SpellType.type_trap in card.requirements:
                    self.cast_trap = True
            
            # Specific named check for Feint
            if isinstance(card, NamedSpell) and card.name == "Feint":
                self.cast_feint = True
                
        return success
