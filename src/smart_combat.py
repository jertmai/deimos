import asyncio
from typing import Optional

from wizwalker.extensions.wizsprinter.sprinty_combat import SprintyCombat, does_card_contain_reqs, SpellType
from wizwalker.extensions.wizsprinter.combat_backends.combat_api import MoveConfig, Move, TargetData, TargetType, NamedSpell, TemplateSpell
import wizwalker.errors
import wizwalker.utils

class SmartCombat(SprintyCombat):
    def __init__(self, client, config_provider, handle_mouseless=False):
        super().__init__(client, config_provider, handle_mouseless)
        self.cast_feint = False
        self.cast_trap = False
        self.cast_aura = False
        self.cast_prism = False
        self.cast_blades = set()
        self.boss_mode = False

    async def handle_combat(self):
        # Reset trackers for new combat
        self.cast_feint = False
        self.cast_trap = False
        self.cast_aura = False
        self.cast_prism = False
        self.cast_blades = set()
        self.boss_mode = False
        await super().handle_combat()

    async def get_alive_boss(self):
        for m in await self.get_members():
            if await m.is_boss() and not await m.is_dead():
                return m
        return None

    async def get_dynamic_priorities(self) -> list[MoveConfig]:
        boss = await self.get_alive_boss()
        self.boss_mode = (boss is not None)
        
        priorities = []
        
        template_blade = TemplateSpell([SpellType.type_blade], False)
        template_trap = TemplateSpell([SpellType.type_trap], False)
        template_aura = TemplateSpell([SpellType.type_aura], False)
        template_damage = TemplateSpell([SpellType.type_damage], False)
        template_aoe = TemplateSpell([SpellType.type_aoe], False)
        template_enchant = TemplateSpell([SpellType.type_enchant], False)
        
        if self.boss_mode:
            boss_target = TargetData(TargetType.type_named, await boss.name(), True)

            if not self.cast_feint:
                priorities.append(MoveConfig(Move(NamedSpell("Feint", False)), target=boss_target))
            if not self.cast_trap:
                priorities.append(MoveConfig(Move(template_trap), target=boss_target))
            if len(self.cast_blades) < 1:
                priorities.append(MoveConfig(Move(template_blade), target=TargetData(TargetType.type_self)))
            if not self.cast_aura:
                priorities.append(MoveConfig(Move(template_aura), target=TargetData(TargetType.type_self)))
                
            priorities.append(MoveConfig(Move(template_aoe, enchant=template_enchant)))
            priorities.append(MoveConfig(Move(template_damage, enchant=template_enchant), target=boss_target))
            priorities.append(MoveConfig(Move(template_aoe)))
            priorities.append(MoveConfig(Move(template_damage), target=boss_target))
        else:
            cards = await self.get_castable_cards()
            available_blades = []
            available_blades_lower = []
            for card in cards:
                if await does_card_contain_reqs(card, template_blade):
                    original_name = await card.name()
                    c_name_lower = original_name.lower()
                    if c_name_lower not in self.cast_blades and c_name_lower not in available_blades_lower:
                        available_blades.append(original_name)
                        available_blades_lower.append(c_name_lower)
                        
            for blade_name in available_blades:
                priorities.append(MoveConfig(Move(NamedSpell(blade_name, False)), target=TargetData(TargetType.type_self)))
            
            # Hit priority
            priorities.append(MoveConfig(Move(template_aoe, enchant=template_enchant)))
            priorities.append(MoveConfig(Move(template_damage, enchant=template_enchant), target=TargetData(TargetType.type_enemy)))
            priorities.append(MoveConfig(Move(template_aoe)))
            priorities.append(MoveConfig(Move(template_damage), target=TargetData(TargetType.type_enemy)))
            
        return priorities

    async def try_execute_config(self, move_config: MoveConfig) -> bool:
        only_enchantable = move_config.move.enchant is not None
        cur_card = await self.try_get_spell(move_config.move.card, only_enchantable=only_enchantable)
        
        if cur_card is None:
            return False

        if cur_card == "pass":
            await self.pass_button()
            self.turn_locked_in = True
            return True

        target = await self.try_get_config_target(move_config.target)
        if target == False or target is None:
            return False

        # If targeting self, TargetType.type_self, target might be our client
        # Let's ensure if it is targeting an enemy and they are somehow dead, we abort or redirect
        if target and hasattr(target, 'is_dead') and await target.is_dead():
            return False

        # Identify Buffs to log them accurately
        name = (await cur_card.name()).lower()
        is_feint = "feint" in name
        template_blade = TemplateSpell([SpellType.type_blade], False)
        template_trap = TemplateSpell([SpellType.type_trap], False)
        template_aura = TemplateSpell([SpellType.type_aura], False)
        template_prism = TemplateSpell([SpellType.type_prism], False)
        template_damage = TemplateSpell([SpellType.type_damage], False)
        template_aoe = TemplateSpell([SpellType.type_aoe], False)
        
        is_blade = await does_card_contain_reqs(cur_card, template_blade)
        is_trap = await does_card_contain_reqs(cur_card, template_trap)
        is_aura = await does_card_contain_reqs(cur_card, template_aura)
        is_prism = await does_card_contain_reqs(cur_card, template_prism)
        is_attack = await does_card_contain_reqs(cur_card, template_damage) or await does_card_contain_reqs(cur_card, template_aoe)

        just_enchanted = False
        if only_enchantable and not await cur_card.is_enchanted():
            enchant_card = await self.try_get_spell(move_config.move.enchant, only_enchants=True)
            if enchant_card != "none" and enchant_card is not None:
                pre_enchant_count = len(await self.get_cards())
                attempts = 0
                while len(await self.get_cards()) == pre_enchant_count and attempts < 3:
                    try:
                        await enchant_card.cast(cur_card, sleep_time=self.config.cast_time*2)
                        await asyncio.sleep(self.config.cast_time*2)
                    except (wizwalker.errors.WizWalkerMemoryError, ValueError):
                        pass
                    attempts += 1
                if attempts >= 3:
                    return False
                self.cur_card_count -= 1
                just_enchanted = True
                await asyncio.sleep(1.0)
            elif enchant_card is None and not move_config.move.enchant.optional:
                return False

        to_cast = await self.try_get_spell(move_config.move.card)
        if to_cast is None:
            # Bug fix: If the enchanted card isn't registered in time, we still return True
            # so the auto-clicker doesn't cast a random other spell this turn.
            return just_enchanted
            
        success = False
        try:
            await to_cast.cast(target, sleep_time=self.config.cast_time)
            await asyncio.sleep(self.config.cast_time)
            success = True
        except (wizwalker.errors.WizWalkerMemoryError, ValueError):
            # Network issue or card state changed during clicking, skip
            pass
            
        if not success:
            return just_enchanted
            
        self.turn_locked_in = True
            
        if is_attack:
            # We attacked, meaning our buffs were consumed. Reset them so we can buff again if enemies survive.
            self.cast_feint = False
            self.cast_prism = False
            self.cast_trap = False
            self.cast_blades = set()
            self.cast_aura = False
        elif is_feint:
            self.cast_feint = True
        elif is_prism:
            self.cast_prism = True
        elif is_trap:
            self.cast_trap = True
        elif is_blade:
            self.cast_blades.add(name)
        elif is_aura:
            self.cast_aura = True
            
        return True

    async def clean_hand(self):
        boss = await self.get_alive_boss()
        self.boss_mode = (boss is not None)
    
        made_action = False
        loop_counter = 0
        
        while loop_counter < 15:
            loop_counter += 1
            cards = await self.get_cards()
            seen_names = set()
            found_discard = False
            
            template_enchant = TemplateSpell([SpellType.type_enchant], False)
            template_damage = TemplateSpell([SpellType.type_damage], False)
            template_aoe = TemplateSpell([SpellType.type_aoe], False)
            
            # 1. Iterate and aggressively discard duplicate cards safely, then refetch array to avoid memory shift errors
            for card in cards:
                c_name = (await card.name()).lower()
                
                is_enchant = await does_card_contain_reqs(card, template_enchant)
                is_attack = await does_card_contain_reqs(card, template_damage) or await does_card_contain_reqs(card, template_aoe)
                
                if is_enchant or is_attack:
                    continue
                    
                should_discard = False
                
                if c_name in seen_names:
                    should_discard = True
                else:
                    seen_names.add(c_name)
                    
                if should_discard:
                    await card.discard(sleep_time=0.2)
                    found_discard = True
                    made_action = True
                    break # Break the for loop so we refetch cards safely!
                    
            if not found_discard:
                break # Hand is fully clean of duplicates/trash
                
        # 2. Pre-enchanting: If we have an enchant and an unenchanted damage/aoe spell and hand is clean, enchant it!
        cards = await self.get_cards()
        template_damage = TemplateSpell([SpellType.type_damage], False)
        template_aoe = TemplateSpell([SpellType.type_aoe], False)
        
        enchants = []
        aoe_hits = []
        single_hits = []
        for card in cards:
            if await does_card_contain_reqs(card, template_enchant):
                enchants.append(card)
            elif not await card.is_enchanted():
                if await does_card_contain_reqs(card, template_aoe):
                    aoe_hits.append(card)
                elif await does_card_contain_reqs(card, template_damage):
                    single_hits.append(card)
                
        if enchants and (aoe_hits or single_hits):
            # Pre-enchant AOE heavily over single-target attacks
            target_hit = aoe_hits[0] if aoe_hits else single_hits[0]
            await enchants[0].cast(target_hit, sleep_time=self.config.cast_time)
            await asyncio.sleep(self.config.cast_time)
            made_action = True
                
        return made_action

    async def try_get_config_target(self, target: TargetData):
        if target is not None and target.target_type == TargetType.type_enemy:
            for enemy in await self.get_enemies():
                if not await enemy.is_dead():
                    return enemy
            return False
        return await super().try_get_config_target(target)

    async def handle_round(self):
        async with self.client.mouse_handler:
            self.config.attach_combat(self) 

            real_round = await self.round_number()
            if getattr(self, 'last_real_round', -1) != real_round:
                self.turn_locked_in = False
            self.last_real_round = real_round
            
            if getattr(self, 'turn_locked_in', False):
                await asyncio.sleep(0.5)
                return

            self.cur_card_count = len(await self.get_cards()) + (await self.get_card_counts())[0]
                
            if not self.had_first_round:
                current_round = real_round - 1
                if current_round > 0:
                    self.turn_adjust -= current_round
            else:
                if self.cur_card_count >= self.prev_card_count and not self.was_pass:
                    await self.on_fizzle()
            self.was_pass = False
            
            member = None
            try:
                member = await wizwalker.utils.maybe_wait_for_any_value_with_timeout(
                    self.get_client_member,
                    timeout=2.0
                )
            except wizwalker.errors.ExceptionalTimeout:
                await self.fail_turn()
            
            if member is not None:
                if await member.is_stunned():
                    await self.fail_turn()
                else:
                    # ALWAYS discard duplicate/useless cards and pre-enchant before choosing our move!
                    try:
                        await self.clean_hand()
                    except (wizwalker.errors.WizWalkerMemoryError, ValueError):
                        pass

                    priorities = await self.get_dynamic_priorities()
                    for p in priorities: 
                        try:
                            if await self.try_execute_config(p):
                                break
                        except (wizwalker.errors.WizWalkerMemoryError, ValueError):
                            pass
                    else:
                        try:
                            await self.pass_button()
                            self.turn_locked_in = True
                        except (wizwalker.errors.WizWalkerMemoryError, ValueError):
                            pass
                        
            self.prev_card_count = self.cur_card_count
            self.had_first_round = True
