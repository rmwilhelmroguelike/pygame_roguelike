from __future__ import annotations

from typing import Callable, Optional, Tuple, TYPE_CHECKING, List, Union

from loader_functions.data_loaders import save_game, load_game
from loader_functions.initialize_new_game import get_constants
from render_functions import render_bar
from feat_stuff import get_all_feats, get_feat_reqs
from equipment_slots import EquipmentSlots
import feat_stuff
import components.enchanter
import traceback
from setup_game import new_game

from procgen import generate_dungeon, generate_town
from entity import Item, Bag
from EventDispatch import EventDispatch
 
import tcod
import tcod.event
import tcod.console
import copy
import math
import os

import pygame_textinput
import pygame
import pygame.event


import actions
from actions import (
    Action,
    BumpAction,
    PickupAction,
    WaitAction,
    RangedAction,
    ToggleCombatModeAction,
    CastSelfBuffAction,
    TakeStairsAction,
    CastSelfHealAction,
    FastMoveAction,
    LongRestAction,
    SummonMonsterAction,
    BurningHandsAction,
)
import colors
import exceptions


if TYPE_CHECKING:
    from engine import Engine

constants = get_constants()
block_size = constants['block_size']
gui_image = pygame.image.load(os.path.join('Dawnlike', 'GUI', 'GUI1.png'))
decor_image = pygame.image.load(os.path.join('Dawnlike', 'Objects', 'Decor0.png'))

MOVE_KEYS = {
    # Arrow keys.
    pygame.K_UP: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_HOME: (-1, -1),
    pygame.K_END: (-1, 1),
    pygame.K_PAGEUP: (1, -1),
    pygame.K_PAGEDOWN: (1, 1),
    # Numpad keys.
    pygame.K_KP_1: (-1, 1),
    pygame.K_KP_2: (0, 1),
    pygame.K_KP_3: (1, 1),
    pygame.K_KP_4: (-1, 0),
    pygame.K_KP_6: (1, 0),
    pygame.K_KP_7: (-1, -1),
    pygame.K_KP_8: (0, -1),
    pygame.K_KP_9: (1, -1),
    # Vi keys.
    #tcod.event.K_h: (-1, 0),
    #tcod.event.K_j: (0, 1),
    #tcod.event.K_k: (0, -1),
    #tcod.event.K_l: (1, 0),
    #tcod.event.K_y: (-1, -1),
    #tcod.event.K_u: (1, -1),
    #tcod.event.K_b: (-1, 1),
    #tcod.event.K_n: (1, 1),
}

WAIT_KEYS = {
    pygame.K_PERIOD,
    pygame.K_KP_5,
    pygame.K_CLEAR,
}

CONFIRM_KEYS = {
    pygame.K_RETURN,
    pygame.K_KP_ENTER,
}

ActionOrHandler = Union[Action, "BaseEventHandler"]
"""An event handler return value which can trigger an action or switch active handlers.

If a handler is returned then it will become the active handler for future events.
If an action is returned it will be attempted and if it's valid then
MainGameEventHandler will become the active handler.
"""

def text_fun():
    # Create TextInput-object
    textinput = pygame_textinput.TextInput()

    screen = pygame.display.set_mode((1000, 200))
    clock = pygame.time.Clock()

    filler = True
    
    while filler:
        screen.fill((225, 225, 225))

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                print(textinput.get_text())
                filler = False

        # Feed it with events every frame
        textinput.update(events)
        # Blit its surface onto the screen
        screen.blit(textinput.get_surface(), (10, 10))

        pygame.display.update()
        clock.tick(30)

    return None

class BaseEventHandler(EventDispatch[ActionOrHandler]):
    def __init__(self):
        pass
        #self.state = self
    def handle_events(self, event: pygame.event) -> BaseEventHandler:
        """Handle an event and return the next active event handler."""
        state = self.dispatch(event)
        if state != None:
            if isinstance(state, BaseEventHandler):
                return state
        else:
            return self
        #    self.state = self
        #return self

    def ev_mousemotion(self, event: pygame.MouseMotion) -> None:
        (x_raw, y_raw) = pygame.mouse.get_pos()
        self.engine.mouse_location = (int(x_raw/block_size),  int(y_raw/block_size))
        pygame.display.update()

    def on_render(self, screen: pygame.display) -> None:
        raise NotImplementedError()

    def ev_quit(self, event: pygame.Quit) -> Optional[Action]:
        raise SystemExit()

    def ev_audiodeviceadded(self, event: pygame.event):
        pass

def text_to_screen(screen, text = '', color = colors.white, size = 16, position = (0, 0), font = 'arial'):
    font = pygame.font.SysFont(font, size)
    image = font.render(text, True, color)
    screen.blit(image, position)


class MainMenu(BaseEventHandler):
    """Handle the main menu rendering and input."""

    def on_render(self, screen: pygame.display) -> None:
        """Render the main menu on a background image."""
        background_image = pygame.image.load("menu_background.png").convert_alpha()
        background_image = pygame.transform.scale(background_image,
                                                  (constants['screen_width']*block_size, constants['screen_height']*block_size))
        screen.blit(background_image, (0, 0))
        text_to_screen(screen, text = 'Generic d20 Roguelike', color = colors.white, size = 32, position = (30*block_size, 5*block_size))
        text_to_screen(screen, text = 'By (Robert Wilhelm)', color = colors.white, size = 32, position = (30*block_size, 8*block_size))
        pygame.display.update()
        for i, text in enumerate(
            ["[C] Continue last game",
             "[B] Play as Orc Barbarian",
             "[D] Play as Dwarf Fighter",
             "[E] Play as Elf Wizard",
             "[F] Play as Human Fighter",
             "[H] Play as Human Cleric",
             "[G] For graphics testing",
             "[Q] to Quit"]
        ):
            text_to_screen(screen, text, position = (20*block_size, (15+i)*block_size))

    def ev_keydown(
        self, event: pygame.KEYDOWN
    ) -> Optional[BaseEventHandler]:

        button = event.key
        if button == pygame.K_q or button == pygame.K_ESCAPE:
            raise SystemExit()
        elif button == pygame.K_c:
            engine = load_game('savegame')
            temp = MainGameEventHandler(engine)
            #temp.state = MainGameEventHandler(engine)
            return temp
        elif button == pygame.K_f:
            temp =  MainGameEventHandler(new_game(char_choice = "human_fighter"))
            #temp.state = MainGameEventHandler(temp.engine)
            return temp
        elif button == pygame.K_b:
            temp = MainGameEventHandler(new_game(char_choice = "orc_barbarian"))
            #temp.state = MainGameEventHandler(temp.engine)
            return temp
        elif button == pygame.K_h:
            temp = MainGameEventHandler(new_game(char_choice = "human_cleric"))
            #temp.state = MainGameEventHandler(temp.engine)
            return temp
        elif button == pygame.K_d:
            temp = MainGameEventHandler(new_game(char_choice = "dwarf_fighter"))
            #temp.state = MainGameEventHandler(temp.engine)
            return temp
        elif button == pygame.K_e:
            temp =  MainGameEventHandler(new_game(char_choice = "elf_wizard"))
            #temp.state = MainGameEventHandler(temp.engine)
            return temp
        elif button == pygame.K_g:
            temp = MainGameEventHandler(new_game(char_choice = "graphics_test"))
            #temp.state = MainGameEventHandler(temp.engine)
            return temp
        else:
            return None

class EventHandler(BaseEventHandler):
    def __init__(self, engine: Engine):
        self.engine = engine
        #self.state = self

    def handle_events(self, event: pygame.event) -> BaseEventHandler:
        """Handle events for input handlers with an engine."""
        action_or_state = self.dispatch(event)
        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state
        if self.handle_action(action_or_state):
            # A valid action was performed.
            if not self.engine.player.is_alive:
                # The player was killed sometime during or after the action.
                return GameOverEventHandler(self.engine)
            return MainGameEventHandler(self.engine) # Return to the main handler.
        return self

    def handle_action(self, action: Optional[Action]) -> bool:
        """Handle actions returned from event methods.

        Returns True if the action will advance a turn.
        """
        if action is None:
            return False
        """
            print("action is None")
            self.state = MainGameEventHandler(self.engine)
            return MainGameEventHandler(self.engine)
        """
        try:
            action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], colors.impossible)
            return False # Skip enemy turn on exceptions

        self.engine.handle_enemy_turns()
        self.engine.update_fov()
        #self.state = MainGameEventHandler(self.engine)
        return MainGameEventHandler(self.engine)

    def on_render(self, screen: pygame.display) -> None:
        self.engine.update_fov()
        pygame.display.update()

class MainGameEventHandler(EventHandler):
    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        action: Optional[Action] = None

        key = event.key
        modifier = event.mod

        player = self.engine.player
        
        # Very ugly hack.  Killing yourself with damage doesn't end game.
        # This checks every turn if you were flagged a corpse and ends game.
        # Even uglier: You can move once here during game over, so waitaction wastes final turn
        if player.char == "%":
            return GameOverEventHandler(self.engine)
            action = WaitAction(player)

        elif key in (MOVE_KEYS) and modifier & pygame.KMOD_SHIFT:
            dx, dy = MOVE_KEYS[key]
            action = FastMoveAction(player, dx, dy)
        elif key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            action = BumpAction(player, dx, dy)
        elif key in (pygame.K_PERIOD, pygame.K_COMMA) and modifier & pygame.KMOD_SHIFT:
            action = TakeStairsAction(player)
        elif key in WAIT_KEYS:
            action = WaitAction(player)
        elif key == pygame.K_q:
            return GameOverEventHandler(self.engine)
        elif key == pygame.K_v:
            return HistoryViewer(self.engine)

        elif key == pygame.K_g:
            action = PickupAction(player)
        elif key == pygame.K_x:
            action = ToggleCombatModeAction(player)

        elif key == pygame.K_i:
            return InventoryActivateHandler(self.engine)
        elif key == pygame.K_d:
            return InventoryDropHandler(self.engine)
        elif key == pygame.K_e:
            return EquipmentHandler(self.engine)
        elif key == pygame.K_SLASH and modifier & pygame.KMOD_SHIFT:
            print(modifier)
            return HelpMenuEventHandler(self.engine)
        elif key == pygame.K_SLASH:
            return LookHandler(self.engine)
        elif key == pygame.K_c:
            return CharacterScreenEventHandler(self.engine)
        elif key == pygame.K_a:
            return LevelUpMenuEventHandler(self.engine)
        elif key == pygame.K_f:
            return FeatSelectionEventHandler(self.engine)
        elif key == pygame.K_r and modifier & pygame.KMOD_SHIFT:
            return RestingEventHandler(self.engine)
        elif key == pygame.K_r:
            return RenameItemEventHandler(self.engine)
        elif key == pygame.K_s and modifier & pygame.KMOD_SHIFT:
            return CastSpellHandler(self.engine)
        elif key == pygame.K_s:
            return SaveGameEventHandler(self.engine)
        elif key == pygame.K_l:
            return LoadGameEventHandler(self.engine)
        elif key == pygame.K_t:
            return SingleRangedAttackHandler(
                self.engine,
                callback = lambda xy: actions.FullAttackRangedAction(self.engine.player, xy),
                )
        elif key == pygame.K_b and modifier & pygame.KMOD_SHIFT:
            return BuffListHandler(self.engine)
        elif key == pygame.K_b:
            shop_found = False
            for shop in self.engine.game_map.shops:
                if shop.x == self.engine.player.x and shop.y == self.engine.player.y:
                    return ShopBuyEventHandler(self.engine)
                    shop_found = True
            if shop_found == False:
                self.engine.message_log.add_message("No shop is here to buy from.", colors.white)
        elif key == pygame.K_n:
            shop_found = False
            for shop in self.engine.game_map.shops:
                if shop.x == self.engine.player.x and shop.y == self.engine.player.y:
                    return ShopSellEventHandler(self.engine)
                    shop_found = True
            if shop_found == False:
                self.engine.message_log.add_message("No shop is here to sell to.", colors.white)
        elif key == pygame.K_u and modifier & pygame.KMOD_SHIFT:
            enchant_found = False
            for enchant in self.engine.game_map.enchant:
                if enchant.x == self.engine.player.x and enchant.y == self.engine.player.y:
                    return EnchantEventHandler(self.engine)
                    enchant_found = True
            if enchant_found == False:
                self.engine.message_log.add_message("You cannot enchant items here.", colors.white)
                    
        # No valid key was pressed
        #if action == None:
        #    action = WaitAction(player)
        return action

CURSOR_Y_KEYS = {
    pygame.K_UP: -1,
    pygame.K_DOWN: 1,
    pygame.K_PAGEUP: -10,
    pygame.K_PAGEDOWN: 10,
}

class HistoryViewer(EventHandler):
    """Print the history on a larger window which can be navigated."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.log_length = len(engine.message_log.messages)
        self.cursor = self.log_length - 1

    def on_render(self, screen: pygame.display) -> None:
        width = 30
        height = 40
        console_width = width*block_size
        console_height = height*block_size
        log_console = pygame.Surface((console_width, console_height))
        if self.engine.player.x <= 30:
            x = 50
        else:
            x = 0
        y = 0
        text_to_screen(log_console, text = "<Message history>", position = (10*16, 2*16))

        # Render the message log using the cursor parameter.
        self.engine.message_log.render_messages(
            log_console,
            0,
            0,
            width - 2,
            height - 2,
            self.engine.message_log.messages,
        )
        screen.blit(log_console, (x*block_size, y*block_size))
        pygame.display.update()

    def ev_keydown(self, event: pygame.KeyDown) -> None:
        # Fancy conditional movement to make it feel right.
        key = event.key
        modifier = event.mod
        if key in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[key]
            if adjust < 0 and self.cursor == 0:
                # Only move from the top to the bottom when you're on the edge.
                self.cursor = self.log_length - 1
            elif adjust > 0 and self.cursor == self.log_length - 1:
                # Same with bottom to top movement.
                self.cursor = 0
            else:
                # Otherwise move while staying clamped to the bounds of the history log.
                self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
        elif key == pygame.K_HOME:
            self.cursor = 0 # Move directly to the top message.
        elif key == pygame.K_END:
            self.cursor = self.log_length - 1 # Move directly to the last message.
        else: # Any other key moves back to the main game state.
            return MainGameEventHandler(self.engine)

class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""

    def ev_keydown(self, event: pygame.KeyDown) -> Optional[ActionOrHandler]:
        """By default any key exits this input handler."""
        if pygame.key in { # Ignore modifier keys.
            pygame.K_LSHIFT,
            pygame.K_RSHIFT,
            pygame.K_LCTRL,
            pygame.K_RCTRL,
            pygame.K_LALT,
            pygame.K_RALT,
        }:
            return None
        return self.on_exit()

    def ev_mousebuttondown(
        self, event: pygame.MouseButtonDown
        ) -> Optional[ActionOrHandler]:
        """By default any mouse click exits this input handler."""
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        """Called when the user is trying to exit or cancel an action.

        By default this returns to the main event handler.
        """
        """
        self.engine.event_handler = MainGameEventHandler(self.engine)
        return None
        """
        return MainGameEventHandler(self.engine)

class GameOverEventHandler(AskUserEventHandler):

    def on_render(self, screen: pygame.display) -> None:
        """Screen to confirm quit command."""
        #super().on_render(screen)
        game_over_screen = pygame.Surface((40*block_size, 20*block_size))
        text_to_screen(game_over_screen, text = f"Do you really wish to quit?  Progress will not be saved.", position = (0, 0))
        text_to_screen(game_over_screen, text = f"'Esc' to quit, any other key to return to game.", position = (0, block_size))
        screen.blit(game_over_screen, (0, 0))
        
    def ev_keydown(self, event: pygame.KeyDown) -> None:
        key = event.key
        if key == pygame.K_ESCAPE:
            raise SystemExit()
        else:
            return MainGameEventHandler(self.engine)

class HelpMenuEventHandler(AskUserEventHandler):
    """Displays Help Menu, with keypress uses.  Any key to abort."""

    def on_render(self, screen: pygame.display) -> None:
        """Screen with Help Menu."""
        #super().on_render(screen)
        x = 0
        y = 0
        help_menu_screen = pygame.Surface((40*block_size, 40*block_size))
        for i, text in enumerate(
            ['Help Menu: Available Buttons:  Any Key to return to game.',
             f"Press Shift for capital letter choices.",
             f"Arrows or Number Keys 1-9 to move/attack.",
             f"'a': Level Up Screen.",
             f"'b': (B)uy from shop.",
             f"'c': Display (C)haracter screen (Your stats)",
             f"'d': (D)rop an item from inventory to ground.",
             f"'e': (E)quipment screen.  Can remove worn gear.",
             f"'f': Choose (F)eats, or see available feats.",
             f"'g': (G)et item from floor.",
             f"'i': (I)nventory display.  Then equip or use items.",
             f"'n': Sell an item to shop.",
             f"'r': (R)ename item in inventory.",
             f"'s': (S)ave game.",
             f"'t': (T)hrow or Shoot ranged weapon.",
             f"'v': (V)iew message history.  Can scroll though past messages.",
             f"'x':  e(X)change melee and ranged weapons.",
             f"'B': Display current (B)uffs on character.",
             f"'Q': (Q)uit game: (Esc) to confirm.  Will not save.",
             f"'S': (S)pell selection screen, cast spells.",
             f"'U': Enchant item in inventory at enchanter's shop.",
             f"'/': Look at monster, item, or feature.",
             f"'<', '>': Take stairs.",
             f"'.', '5': Wait one turn.",
             f"'?', This Help screen."]
        ):
            text_to_screen(help_menu_screen, text, position = (80, 80+16*i))
        screen.blit(help_menu_screen, (0, 0))

    def ev_keydown(self, event: pygame.KeyDown) -> None:
        return MainGameEventHandler(self.engine)

class TownPortalEventHandler(AskUserEventHandler):
    """Handles town portal to/from town.  Esc to abort, Q to use."""

    def on_render(self, screen: pygame.display) -> None:
        """Screen to confirm or abort town portal."""
        #super().on_render(screen)
        if self.engine.player.x <= 30:
            x = 50
        else:
            x = 0
        y = 0
        town_portal_screen = pygame.Surface((30*block_size, 20*block_size))
        text_to_screen(town_portal_screen, text = f"You have activated a town portal.", position = (0,0))
        text_to_screen(town_portal_screen, text = f"'Y' to confirm, 'Esc' to abort.", position = (0, block_size*1))
        screen.blit(town_portal_screen, (0,0))

    def ev_keydown(self, event: pygame.KeyDown) -> Optional[ActionOrHandler]:
        from loader_functions.initialize_new_game import get_constants
        constants = get_constants()
        player = self.engine.player
        engine = self.engine
        key = event.key

        if key == pygame.K_ESCAPE or key == pygame.K_y:
            if key == pygame.K_ESCAPE:
                return MainGameEventHandler(self.engine)
            if key == pygame.K_y:
                if engine.game_map.dungeon_level > 0:
                    engine.last_level = engine.game_map.dungeon_level
                    engine.game_map = generate_town(
                        engine = engine,
                        max_rooms = constants['max_rooms'],
                        room_min_size = constants['room_min_size'],
                        room_max_size = constants['room_max_size'],
                        map_width = constants['map_width'],
                        map_height = constants['map_height'],
                    )
                else:
                    engine.game_map = generate_dungeon(
                        max_rooms = constants['max_rooms'],
                        room_min_size = constants['room_min_size'],
                        room_max_size = constants['room_max_size'],
                        map_width = constants['map_width'],
                        map_height = constants['map_height'],
                        engine = engine,
                        dungeon_level = engine.last_level,
                        stairs = 1
                    )
                    engine.last_level = 0
                engine.update_fov()
                return MainGameEventHandler(engine)

class StartMenuEventHandler(AskUserEventHandler):
    """Selects New game or Loads save.  Esc to quit."""
    """No longer used, see setup_game."""

    def on_render(self, screen: pygame.display) -> None:
        """Displays New Game/Load Game selection screen.
        """
        #super().on_render(screen)
        x = 0
        y = 0

        start_menu_screen = pygame.Surface((40*block_size, 20*block_size))
        for i, text in enumerate(
            'Select an Option',
            "Hit 'Z' to load saved game,",
            "'N' for new Dwarf Fighter,",
            "'H' for new Human Fighter,"
            "'W' for new Elf Wizard,",
            "'G' for graphics testing,",
            "or 'Esc' to quit."
        ):
            text_to_screen(start_menu_screen, text, position = (80, 80+16*i))
        screen.blit(help_menu_screen, (0, 0))

    def ev_keydown(self, event: pygame.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key

        if key == pygame.K_z:
            #self.engine.event_handler = MainGameEventHandler(self.engine)
            #present(self.console)
            #self.engine = load_game()
            #self.engine.screen_reset = True
            return MainGameEventHandler(self.engine)
            #self.engine.update_fov()
        elif key in (pygame.K_h, pygame.K_n, pygame.K_w):
            return MainGameEventHandler(self.engine)
        elif key == pygame.K_ESCAPE:
            raise SystemExit()

class UseBagHandler(AskUserEventHandler):
    """Uses a Bag, take item out or put item in."""

    def on_render(self, screen: pygame.display) -> None:
        """Just displays take out or put in options."""
        #super().on_render(screen)
        player = self.engine.player
        if self.engine.player.x <= 30:
            x = 50
        else:
            x = 0
        y = 0
        bag_screen = pygame.Surface((40*block_size, 20*block_size))
        for i, text in enumerate([
            f"{player.name}'s Bag use.",
            "Press 'p' to place an item in the bag.",
            "Press 't' to take an item from the bag.",
            "Press 'Esc' to abort.",]
        ):
            text_to_screen(bag_screen, text, position = (80, 80+16*i))
        screen.blit(bag_screen, (0, 0))

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key

        if key == pygame.K_t:
            return TakeFromBagHandler(self.engine)

        if key == pygame.K_p:
            return PlaceInBagHandler(self.engine)
        
        if key == pygame.K_q or key == pygame.K_ESCAPE:
            return MainGameEventHandler(self.engine)
        
class CastSpellHandler(AskUserEventHandler):
    """Casts a spell known"""

    def on_render(self, screen: pygame.display) -> None:
        """Displays available spells and mana costs."""
        #super().on_render(screen)
        player = self.engine.player
        if self.engine.player.x <= 30:
            x = 50
        else:
            x = 0
        y = 0
        cast_spell_menu = pygame.Surface((30*block_size, 50*block_size))
        text_to_screen(cast_spell_menu, text = f"{player.name}'s spells:", position = (0, 0))
        if len(list(player.battler.spells)) == 0:
            text_to_screen(cast_spell_menu, text = "You know no spells.  Esc or Q to quit", position = (0, block_size))
        else:
            text_to_screen(cast_spell_menu, text = f"Select a letter to cast spell, Esc or Q to quit", position = (0, block_size))
            text_to_screen(cast_spell_menu, text = f"You currently have {player.battler.mana} mana remaining", position = (0, block_size*2))
            all_spells_list = list(player.battler.spells)
            all_spells_list.sort()
            current_spells_list = []
            for i in range(len(all_spells_list)):
                if player.battler.spells[all_spells_list[i]] <= player.level.current_level:
                    current_spells_list.append(all_spells_list[i])
            for i in range(len(current_spells_list)):
                text_to_screen(cast_spell_menu, text = f"Press '{chr(i+97)}' for {current_spells_list[i]}: {player.battler.spells[current_spells_list[i]]} Mana.", position = (0, block_size*(i+3)))
        screen.blit(cast_spell_menu, (0, 0))
        render_bar(screen, self.engine)

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key

        all_spells_list = list(player.battler.spells)
        all_spells_list.sort()
        current_spells_list = []
        for i in range(len(all_spells_list)):
            if player.battler.spells[all_spells_list[i]] <= player.level.current_level:
                current_spells_list.append(all_spells_list[i])
        letter_found = key - 97

        if letter_found in range(len(current_spells_list)):
            if current_spells_list[letter_found] in ("Mage Armor", "Shield", "Magic Weapon", "Alter Self"):
                return CastSelfBuffAction(player, current_spells_list[letter_found])
            elif current_spells_list[letter_found] in ("Magic Missile"):
                return SingleRangedAttackHandler(
                    self.engine,
                    callback = lambda xy: actions.CastMagicMissileAction(self.engine.player, xy),
                    )
            elif current_spells_list[letter_found] in ("Scorching Ray"):
                return SingleRangedAttackHandler(
                    self.engine,
                    callback = lambda xy: actions.CastScorchingRayAction(self.engine.player, xy),
                    )
            elif current_spells_list[letter_found] in ("Shocking Grasp"):
                return SingleMeleeAttackHandler(
                    self.engine,
                    callback = lambda xy: actions.CastShockingGraspAction(self.engine.player, xy),
                    )
            elif current_spells_list[letter_found] in ("Ray of Enfeeblement"):
                return SingleRangedAttackHandler(
                    self.engine,
                    callback = lambda xy: actions.CastRayOfEnfeeblementAction(self.engine.player, xy),
                    )
            elif current_spells_list[letter_found] in ("Cure Light Wounds", "Cure Moderate Wounds", "Cure Serious Wounds", "Cure Critical Wounds"):
                return CastSelfHealAction(player, current_spells_list[letter_found])
            elif current_spells_list[letter_found] in ("Summon Monster 1", "Summon Monster 2", "Summon Monster 3"):
                mana = player.battler.spells[current_spells_list[letter_found]]
                return SummonMonsterHandler(
                    self.engine,
                    callback = lambda xy: actions.SummonMonsterAction(self.engine.player, xy, current_spells_list[letter_found], mana),
                    )
            elif current_spells_list[letter_found] in ("Burning Hands"):
                return ConeAreaAttackHandler(
                    self.engine,
                    callback = lambda xy: actions.BurningHandsAction(self.engine.player, xy, current_spells_list[letter_found], mana = 1, radius = 3),
                    )

        if key == pygame.K_ESCAPE:
            return MainGameEventHandler(self.engine)


class FeatSelectionEventHandler(AskUserEventHandler):
    """Selects new feats.  Esc or Q to quit."""

    def on_render(self, screen: pygame.display) -> None:
        """Displays feat selection screen."""
        #super().on_render(screen)
        player = self.engine.player
        feat_menu = pygame.Surface((60*block_size, 50*block_size))
        text_to_screen(feat_menu, text = f"Select a letter to learn feat or improve stat, Esc or Q to quit.", position = (0, 0))
        text_to_screen(feat_menu, text = f"You have {player.battler.feats_to_take} feats to learn, and {player.battler.stats_to_take} stat points to spend.", position = (0, block_size*1))
        current_feats_list = list(player.battler.combat_feats)
        for i in range(len(current_feats_list)):
            if player.battler.combat_feats[current_feats_list[i]] > 1:
                text_to_screen(feat_menu, text = f"Known feat: {current_feats_list[i]} (X{player.battler.combat_feats[current_feats_list[i]]})", position = (0, block_size*(3+i)))
            else:
                text_to_screen(feat_menu, text = f"Known feat: {current_feats_list[i]}.", position = (0, block_size*(3+i)))
        taken_once_feats, taken_multiple_feats = get_all_feats()
        combined_feats = {**taken_once_feats, **taken_multiple_feats}
        taken_multiple_feats_list = list(taken_multiple_feats)
        taken_once_feats_list = list(taken_once_feats)
        possible_feats_list = list((set(taken_once_feats_list) - set(current_feats_list))|set(taken_multiple_feats_list))
        main_feats_list = copy.deepcopy(possible_feats_list)
        for i in range(len(possible_feats_list)):
            if get_feat_reqs(player, combined_feats[possible_feats_list[i]]) == False:
                main_feats_list.remove(possible_feats_list[i])
        main_feats_list.sort()
        for j in range(len(main_feats_list)):
            text_to_screen(feat_menu, text = f"Select '{chr(j+97)}' to learn {main_feats_list[j]}.", position = (0, block_size*(3+len(current_feats_list)+j)))
        stat = list(["Str","Dex","Con","Int","Wis","Cha"])
        for k in range(6):
            text_to_screen(feat_menu, text = f"Select '{chr(len(main_feats_list)+k+97)}' to gain {stat[k]}.", position = (0, block_size*(3+len(current_feats_list)+len(main_feats_list)+k)))
        screen.blit(feat_menu, (0, 0))
        render_bar(screen, self.engine)

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key

        current_feats_list = list(player.battler.combat_feats)
        taken_once_feats, taken_multiple_feats = get_all_feats()
        combined_feats = {**taken_once_feats, **taken_multiple_feats}
        taken_multiple_feats_list = list(taken_multiple_feats)
        taken_once_feats_list = list(taken_once_feats)
        possible_feats_list = list((set(taken_once_feats_list) - set(current_feats_list))|set(taken_multiple_feats_list))
        main_feats_list = copy.deepcopy(possible_feats_list)
        for i in range(len(possible_feats_list)):
            if get_feat_reqs(player, combined_feats[possible_feats_list[i]]) == False:
                main_feats_list.remove(possible_feats_list[i])
        main_feats_list.sort()
        letter_found = key - 97

        if player.battler.feats_to_take > 0:
            if letter_found in range(len(main_feats_list)):
                if main_feats_list[letter_found] in player.battler.combat_feats:
                    player.battler.combat_feats[main_feats_list[letter_found]] += 1
                else:
                    player.battler.combat_feats[main_feats_list[letter_found]] = 1
                player.battler.feats_to_take -= 1
                return MainGameEventHandler(self.engine)

        if player.battler.stats_to_take > 0:
            stat_choice = letter_found - len(main_feats_list)
            if stat_choice >= 0 and stat_choice < 6:
                player.battler.stats_to_take -= 1
                if stat_choice == 0:
                    player.battler.strength += 1
                elif stat_choice == 1:
                    player.battler.dexterity += 1
                elif stat_choice == 2:
                    player.battler.constitution += 1
                elif stat_choice == 3:
                    player.battler.intelligence += 1
                elif stat_choice == 4:
                    player.battler.wisdom += 1
                elif stat_choice == 5:
                    player.battler.charisma += 1
                else:
                    raise Impossible(f"This statistic does not exist.")
                

        if key == pygame.K_q or key == pygame.K_ESCAPE:
            return MainGameEventHandler(self.engine)

class BuffListHandler(AskUserEventHandler):
    """Displays Buffs and durations.  No interaction.  Esc to quit."""

    def on_render(self, screen: pygame.display) -> None:
        """Display character's buff list.
        """
        #super().on_render(screen)
        if self.engine.player.x <= 30:
            x = 50
        else:
            x = 0
        y = 0
        player = self.engine.player

        title = f"{player.name}'s current buffs."
        buff_screen = pygame.Surface((30*block_size, 50*block_size))
        text_to_screen(buff_screen, text = title, position = (0, 0))
        text_to_screen(buff_screen, text = f"{player.name}'s Buffs: (Turn is now {self.engine.current_turn})", position = (0, 2*block_size))
        y_hold = 3
        if len(list(player.battler.current_buffs)) == 0:
            y_hold += 1
            text_to_screen(buff_screen, text = f"You have no buffs active.", position = (x*block_size, y_hold*block_size))
        else:
            buffs = list(player.battler.current_buffs)
            buffs.sort()
            for i in range(len(buffs)):
                y_hold += 1
                text_to_screen(buff_screen, f"{buffs[i]}: {player.battler.current_buffs[buffs[i]][0] - self.engine.current_turn} turns remaining.",
                               position = (x*block_size, y_hold*block_size))
        text_to_screen(buff_screen, text = f"'Esc' or 'Q' to quit.", position = (x*block_size, (y_hold + 2)*block_size))
        screen.blit(buff_screen, (0, 0))

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key

        if key == pygame.K_ESCAPE or key == pygame.K_q:
            return MainGameEventHandler(self.engine)

class CharacterScreenEventHandler(AskUserEventHandler):
    """Displays character statistics.  No interaction.  Esc to quit."""

    def on_render(self, screen: pygame.display) -> None:
        """Display character screen.
        """
        #super().on_render(screen)

        x = 0
        y = 0
        width = 70
        height = 30
        player = self.engine.player

        char_screen = pygame.Surface((width*block_size, height*block_size))
        """
        for i, text in enumerate(
            ["[F] Play as Human Fighter",
             "[D] Play as Dwarf Fighter",
             "[E] Play as Elf Wizard",
             "[H] Play as Human Cleric",
             "[C] Continue last game",
             "[G] For graphics testing",
             "[Q] to Quit"]
        ):
        """
        if player.equipment.main_hand == None:
            main_text = f"Melee Damage: {player.battler.unarmed_num_dice}d{player.battler.unarmed_size_dice} + {player.battler.melee_to_damage} (+{player.battler.melee_to_hit} to hit)."
        else:
            main_text = f"Melee Damage: {player.equipment.main_hand.equippable.weapon_num_dice}d{player.equipment.main_hand.equippable.weapon_size_dice} + {player.battler.melee_to_damage}. (+{player.battler.melee_to_hit} to hit.)"
        if player.equipment.ranged != None:
            ranged_text = f"Ranged Damage: {player.equipment.ranged.equippable.weapon_num_dice}d{player.equipment.ranged.equippable.weapon_size_dice} + {player.battler.ranged_to_damage}. (+{player.battler.ranged_to_hit} to hit.)"
        else:
            ranged_text = ""
        for i, char_text in enumerate(
            [f"{player.name}'s vital statistics",
             f"Character Information",
             f"{player.name}: Level {player.level.current_level} {player.battler.hit_dice}.",
             f"Experience: {player.level.current_xp}.",
             f"Experience to Level: {player.level.experience_to_next_level}.",
             f"Maximum HP: {player.battler.max_hp}.  Maximum Mana: {player.battler.max_mana}",
             main_text,
             f"Strength: {player.battler.current_str}({player.battler.strength}). Dexterity: {player.battler.current_dex}({player.battler.dexterity}).  Constitution: {player.battler.current_con}({player.battler.constitution})",
             f"Intelligence: {player.battler.current_int}({player.battler.intelligence}).  Wisdom: {player.battler.current_wis}({player.battler.wisdom}).  Charisma: {player.battler.current_cha}({player.battler.charisma}).",
             ranged_text,
             "",
             f"AC: {player.battler.current_ac}. Dex to AC: {player.battler.dex_to_ac}.",
             "",
             f"BAB: +{player.battler.bab}. Saves: Fort: (+{player.battler.fort_save}), Reflex: (+{player.battler.reflex_save}), Will: (+{player.battler.will_save})."]
            ):
            text_to_screen(char_screen, text = char_text, position = (x, (y + 2 + i)*block_size))
        feats_string = "Feats: "
        if len(player.battler.combat_feats) == 0:
            feats_string = feats_string + "None."
        else:
            current_feats_list = list(player.battler.combat_feats)
            for i in range(len(current_feats_list)):
                feats_string += current_feats_list[i] + " "
        text_to_screen(char_screen, text = feats_string, position = (x + 1, (y + 18)*block_size))
        screen.blit(char_screen, (0, 0))

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key

        if key == pygame.K_ESCAPE or key == pygame.K_q:
            return MainGameEventHandler(self.engine)
            
class LevelUpMenuEventHandler(AskUserEventHandler):
    """Selects level up stat gain.  Escape or Q to leave."""

    def on_render(self, screen: pygame.display) -> None:
        """Displays Level Up screen.
        """
        #super().on_render(screen)
        x = 0
        y = 0

        level_screen = pygame.Surface((20*block_size, 15*block_size))
        feats_gained = 0
        next_level = self.engine.player.level.current_level + 1
        if self.engine.player.level.current_xp >= self.engine.player.level.experience_to_next_level:
            text_to_screen(level_screen, text = f"Congratulations! You are now level {self.engine.player.level.current_level + 1}!",
                           position = (x*block_size,(y + 1)*block_size))
            text_to_screen(level_screen, text = f"Max hps increase by placeholder!", position =  (x*block_size, (y + 2)*block_size))
            if self.engine.player.battler.hit_dice == "Fighter":
                text_to_screen(level_screen, text = f"Base Attack Bonus (BAB) increases by 1!", position = (x*block_size, (y + 3)*block_size))
            elif self.engine.player.battler.hit_dice == "Wizard":
                if (next_level) % 2 == 1:
                    text_to_screen(level_screen, text = f"Base Attack Bonus (BAB) increases by 1!", position = (x*block_size, (y + 3)*block_size))
            if self.engine.player.battler.hit_dice == "Fighter":
                feats_gained += 1
            elif (next_level) % 2 == 1:
                feats_gained += 1
            if self.engine.player.battler.hit_dice == "Wizard":
                if (next_level) % 5 == 0:
                    feats_gained += 1
            if feats_gained > 0:
                text_to_screen(level_screen, text = f"You have {feats_gained} more feat(s) to learn!", position = (x*block_size, (y + 4)*block_size))
            if next_level % 4 == 0:
                text_to_screen(level_screen, text = f"You have {self.engine.player.battler.stats_to_take+1} stat points to spend.", position = (x*block_size, (y + 5)*block_size))
        else:
            text_to_screen(level_screen, text = f"You do not have sufficient experience to level.", position = (x*block_size, (y + 2)*block_size))

        text_to_screen(level_screen, text = f"Escape or 'q' to continue.", position = (x*block_size, (y + 9)*block_size))
        screen.blit(level_screen, (0,0))
        render_bar(screen, self.engine)

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key

        if key == pygame.K_ESCAPE or key == pygame.K_q:
            if player.level.current_xp >= player.level.experience_to_next_level:
                self.engine.player.battler.hp = self.engine.player.battler.max_hp
                player.level.current_xp -= player.level.experience_to_next_level
                player.level.current_level += 1
                if player.level.current_level % 4 == 0:
                    self.engine.player.battler.stats_to_take += 1
                if player.battler.hit_dice == "Fighter":
                    self.engine.player.battler.feats_to_take += 1 #Fighters get feats every level
                elif player.level.current_level % 2 == 1:
                    self.engine.player.battler.feats_to_take += 1
                if player.battler.hit_dice == "Wizard":
                    if player.level.current_level % 5 == 0:
                        self.engine.player.battler.feats_to_take += 1
                player.battler.hp = player.battler.max_hp
                player.battler.mana = player.battler.max_mana
            return MainGameEventHandler(self.engine)        

class ShopBuyEventHandler(AskUserEventHandler):
    """This handler selects items to buy from a shop."""


    TITLE = "Shop items for sale"

    def on_render(self, screen: pygame.display) -> None:
        #super().on_render(screen)
        for shop in self.engine.game_map.shops:
            if shop.x == self.engine.player.x and shop.y == self.engine.player.y:
                number_of_items_for_sale = len(shop.for_sale)
                items_for_sale = shop.for_sale

        height = number_of_items_for_sale + 2

        if height <= 3:
            height = 3

        width = 30

        if self.engine.player.x <= 30:
            x = 50
        else:
            x = 0
        y = 0

        buy_screen = pygame.Surface((width*block_size, height*block_size))

        if number_of_items_for_sale > 0:
            for i, item in enumerate(items_for_sale):
                item_key = chr(ord("a") + i)
                text_to_screen(buy_screen, text = f"({item_key}) {item.name} ${item.gold_value}",
                               position = (0*block_size, (y + i + 1)*block_size))
        else:
            text_to_screen(buy_screen, text = "(Empty)", position = (x*block_size, (y + 1)*block_size))
        screen.blit(buy_screen, (x*block_size, y*block_size))
        render_bar(screen, self.engine)

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        index = key - pygame.K_a
        for shop in self.engine.game_map.shops:
            if shop.x == self.engine.player.x and shop.y == self.engine.player.y:
                number_of_items_for_sale = len(shop.for_sale)
                items_for_sale = shop.for_sale

        if 0 <= index <= 26:
            try:
                selected_item = items_for_sale[index]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", colors.invalid)
                return None
            return self.buy_item(selected_item, player)
        return super().ev_keydown(event)

    def buy_item(
        self, item: Item, player: Entity
        ) -> Optional[ActionOrHandler]:
        """Called when the user selects a valid item."""
        if len(player.inventory.items) >= player.inventory.capacity:
            raise exceptions.Impossible("Your inventory is full")
        elif player.battler.gold >= item.gold_value:
            stacking = False
            for i in range(len(player.inventory.items)):
                if player.inventory.items[i].name == item.name:
                    if item.can_stack == True:
                        player.inventory.items[i].number_in_stack += 1
                        stacking = True
                        self.engine.message_log.add_message(f"You buy another {item.name} for {item.gold_value} gold.", colors.yellow)
            if stacking == False:
                clone_item = copy.deepcopy(item)
                clone_item.parent = player.inventory
                player.inventory.items.append(clone_item)
                self.engine.message_log.add_message(f"You buy {item.name} for {item.gold_value} gold.", colors.yellow)
            player.battler.gold -= item.gold_value
        else :
            self.engine.message_log.add_message("You don't have the gold for that.", colors.yellow)

class TakeFromBagHandler(AskUserEventHandler):
    """This handler takes from a bag, placing items in inventory."""

    TITLE = "Items in this bag."

    def on_render(self, screen: pygame.display) -> None:
        """Render a bag's inventory."""
        #super().on_render(screen)
        number_of_items_in_bag = len(self.engine.enchanting_item.bag_inventory.items)

        height = number_of_items_in_bag + 2

        if height <= 3:
            height = 3

        if self.engine.player.x <= 30:
            x = 50
        else:
            x = 0
        y = 0

        width = 30
        take_screen = pygame.Surface(((width*block_size), (height*block_size)))

        text_to_screen(take_screen, text = "Items in this bag.", position = (x*block_size, y*block_size))

        if number_of_items_in_bag > 0:
            for i, item in enumerate(self.engine.enchanting_item.bag_inventory.items):
                item_key = chr(ord("a") + i)
                num_in_pack = ""
                item_gold_str = ""
                if self.engine.enchanting_item.bag_inventory.items[i].number_in_stack > 1:
                    num_in_pack = f" ({self.engine.enchant_item.bag_inventory.items[i].number_in_stack})"
                if item.gold_value > 0:
                    item_gold_str = f" ${item.gold_value}"
                text_to_screen(take_screen, text = (f"({item_key}) {item.name}" + num_in_pack + item_gold_str),
                               position = (x*block_size, (y + i + 1)*block_size))
        else:
            text_to_screen(take_screen, text = "(Empty)", position = ((x + 1)*block_size, (y + 1)*block_size))
        screen.blit(take_screen, (x*block_size, y*block_size))

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        index = key - pygame.K_a
        bag = self.engine.enchanting_item

        if 0 <= index <= 26:
            try:
                selected_item = self.engine.enchanting_item.bag_inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", colors.invalid)
                return None
            if len(player.inventory.items) >= player.inventory.capacity:
                self.engine.message_log.add_message(f"You can't remove items from bags, inventory is full.")
            else:
                player.inventory.items.append(selected_item)
                self.engine.enchanting_item.bag_inventory.items.remove(selected_item)
                self.engine.message_log.add_message(f"You take the {selected_item.name} from the {bag.name}.")
        else:
            return super().ev_keydown(event)

class InventoryEventHandler(AskUserEventHandler):
    """This handler lets the user select an item.

    What happens then depends on the subclass.
    """



    def on_render(self, screen: pygame.display) -> None:
        """Render an inventory menu, which displays the items in the inventory,
        and the letter to select them.  Will move to a different position based
        on where the player is located, so the player can always see where
        they are.
        """
        #super().on_render(screen)
        number_of_items_in_inventory = len(self.engine.player.inventory.items)

        height = number_of_items_in_inventory + 2

        if height <= 3:
            height = 3

        if self.engine.player.x <= 30:
            x = 50
        else:
            x = 0
        y = 0

        width = 30

        inv_screen = pygame.Surface((width*block_size, 40*block_size))
        inv_screen.fill((0, 0, 0))
        if number_of_items_in_inventory > 0:
            for i, item in enumerate(self.engine.player.inventory.items):
                item_key = chr(ord("a") + i)
                num_in_pack = ""
                equip_status = ""
                item_gold_str = ""
                if self.engine.player.equipment.main_hand == item:
                    if self.engine.player.equipment.main_hand.equippable.slot == EquipmentSlots.MAIN_HAND:
                        equip_status = " (in main hand)"
                    elif self.engine.player.equipment.main_hand.equippable.slot == EquipmentSlots.TWO_HAND:
                        equip_status = " (in both hands)"
                elif self.engine.player.equipment.off_hand == item:
                    equip_status = " (on off hand)"
                elif self.engine.player.equipment.ranged == item:
                    equip_status = " (as ranged)"
                elif self.engine.player.equipment.body == item:
                    equip_status = " (worn on body)"
                elif self.engine.player.equipment.neck == item:
                    equip_status = " (worn on neck)"
                elif self.engine.player.equipment.waist == item:
                    equip_status = " (on waist)"
                elif self.engine.player.equipment.lring == item:
                    equip_status = " (on left hand)"
                elif self.engine.player.equipment.rring == item:
                    equip_status = " (on right hand)"
                elif self.engine.player.equipment.head == item:
                    equip_status = " (on head)"
                elif self.engine.player.equipment.cloak == item:
                    equip_status = " (worn on shoulders)"
                elif self.engine.player.equipment.eyes == item:
                    equip_status = " (worn on face)"
                elif self.engine.player.equipment.shirt == item:
                    equip_status = " (worn about torso)"
                elif self.engine.player.equipment.wrists == item:
                    equip_status = " (worn on wrists)"
                elif self.engine.player.equipment.feet == item:
                    equip_status = " (worn on feet)"
                elif self.engine.player.equipment.hands == item:
                    equip_status = " (worn on hands)"
                elif self.engine.player.equipment.misc == item:
                    equip_status =  " (worn slotless)"
                if self.engine.player.inventory.items[i].number_in_stack > 1:
                    num_in_pack = f" ({self.engine.player.inventory.items[i].number_in_stack})"
                if item.gold_value > 0:
                    item_gold_str = f" ${item.gold_value}"
                text_to_screen(inv_screen, text = (f"({item_key}) {item.name}" + equip_status + num_in_pack + item_gold_str),
                               position = (0*block_size, (y + i + 1)*block_size))
        else:
            text_to_screen(inv_screen, text = "(Empty)", position = (0*block_size, (y + 1)*block_size))
        screen.blit(inv_screen, (x*block_size, 0))
        render_bar(screen, self.engine)

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        index = key - pygame.K_a


        if self.engine.enchant_now == False:
            if 0 <= index <= 26:
                try:
                    selected_item = player.inventory.items[index]
                except IndexError:
                    self.engine.message_log.add_message("Invalid entry.", colors.invalid)
                    return None
                return self.on_item_selected(selected_item)
            return super().ev_keydown(event)
        else:
            return None

class PlaceInBagHandler(InventoryEventHandler):
    """Places one item from inventory in bag."""
    
    TITLE = "Choose an item to place in the bag."

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Return the action for the selected item."""
        
        return None

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        modifier = event.mod
        
        index = key - pygame.K_a

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message(f"Invalid entry.", colors.invalid)
                return None
            bag = self.engine.enchanting_item #Need to rename to some chosen item
            if len(bag.bag_inventory.items) >= bag.bag_inventory.capacity:
                self.engine.message_log.add_message(f"Your bag is full.")
            elif selected_item in (player.equipment.main_hand, player.equipment.off_hand, player.equipment.body,
                        player.equipment.neck, player.equipment.ranged, player.equipment.waist,
                        player.equipment.lring, player.equipment.rring, player.equipment.head,
                        player.equipment.cloak, player.equipment.eyes, player.equipment.shirt,
                        player.equipment.wrists, player.equipment.feet, player.equipment.hands,
                        player.equipment.misc):
                self.engine.message_log.add_message("You can't place something you are wearing in a bag.", colors.white)
            elif selected_item.can_stack == True:
                self.engine.message_log.add_message("Stacking items not implemented for bags.", colors.white)
            elif selected_item == bag:
                self.engine.message_log.add_message("You can't place a bag in itself.", colors.white)
            else:
                self.engine.message_log.add_message(f"You place the {selected_item.name} in the {bag.name}.", colors.white)
                bag.bag_inventory.items.append(selected_item)
                player.inventory.items.remove(selected_item)
        return super().ev_keydown(event)

class RestingEventHandler(AskUserEventHandler):
    """Rest multiple turns.  Enter number of turns, or "a" for all hps/mps."""
    def __init__(self, engine: Engine, num_turns: str = ""):
        self.engine = engine
        self.num_turns = num_turns
    """Enters number of turns"""

    TITLE = "Rest how many turns? ('a' for all hps/mana recovered.)"

    def on_render(self, screen: pygame.display) -> None:
        """Renders text being entered.
        """
        #super().on_render(screen)
        height = 2
        width = 30
        if self.engine.player.x <= 30:
            x = 50
        else:
            x = 0
        y = 0

        num_turns_line = pygame.Surface((width*block_size, height*block_size))
        text_to_screen(num_turns_line, text = "Rest how many turns? ('a' for all hps/mana recovered.)", position = (0, 0))
        text_to_screen(num_turns_line, text = self.num_turns,
                       position = (0, block_size))
        screen.blit(num_turns_line, (x*block_size, 0))

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        modifier = event.mod
        index = key - tcod.event.K_a

        if key == pygame.K_ESCAPE:
            self.engine.message_log.add_message("Rest aborted.", colors.white)
            return MainGameEventHandler(self.engine)
        elif key == pygame.K_a:
            return LongRestAction(player, 0)
        elif key == pygame.K_RETURN:
            if self.num_turns == "":
                self.engine.message_log.add_message("Rest aborted.", colors.white)
                return MainGameEventHandler(self.engine)
            else:
                return LongRestAction(player, int(self.num_turns))
        else:
            if key > 47 and key < 58:
                self.num_turns += chr(ord("a") + index)  # 0 to 9
            pygame.display.update()
            

class TextEntryEventHandler(AskUserEventHandler):
    def __init__(self, engine: Engine, input_text: str = ""):
        self.engine = engine
        self.input_text = input_text
        self.TITLE = "Enter text here."
    """For user to enter text, naming items or save files."""

    def on_render(self, screen: pygame.display) -> None:
        """Renders text being entered.
        """
        #super().on_render(screen)

        height = 5
        width = 30

        if self.engine.player.x <= 30:
            x = 50
        else:
            x = 0

        y = 0

        text_screen = pygame.Surface((width*block_size, height*block_size))

        text_to_screen(text_screen, text = self.TITLE, position = (0*block_size, y*block_size))
        text_to_screen(text_screen, text = f"{self.input_text}",
                       position = (0*block_size, (y + 1)*block_size))
        screen.blit(text_screen, (x*block_size, 0))
        pygame.display.update()

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        modifier = event.mod
        
        index = key - tcod.event.K_a

        print(f"{chr(ord('a') + index)} in text input self.input_text currently {self.input_text}")
        if key != pygame.K_ESCAPE and key != pygame.K_RETURN:
            if modifier & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT): #Ugly hack, lshift or rshift
                if key == pygame.K_EQUALS:
                    self.input_text += "+"
                if 0 <= index < 26:
                    self.input_text += chr(ord("a") + index - 32)
            else: #Need check for valid ascii, index range?
                self.input_text += chr(ord("a") + index)
                return None
        else:
            self.engine.enchant_now = False
            self.engine.message_log.add_message(f"Text entered.")
            return None

        return super().ev_keydown(event)

class LoadGameEventHandler(TextEntryEventHandler):
    def __init__(self, engine: Engine, input_text: str = ""):
        self.engine = engine
        self.input_text = input_text
        self.TITLE = "Enter load game name:"
    """Load from game slot, name text input."""

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        modifier = event.mod
        
        index = key - tcod.event.K_a

        if key == pygame.K_ESCAPE:
            self.engine.message_log.add_message(f"Load game aborted.")
            return MainGameEventHandler(self.engine)
        elif key == pygame.K_RETURN:
            if self.input_text == "":
                self.input_text = "savegame"
            self.engine.message_log.add_message(f"Game attempting to load {self.input_text}.")
            #message log needs render or it never is visible to player.
            print(f"Game attempting to load {self.input_text}.")
            engine = load_game(self.input_text)
            temp = MainGameEventHandler(engine)
            #temp.state = MainGameEventHandler(engine)
            return temp
        elif modifier & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT): #Ugly hack, lshift or rshift
            if key == pygame.K_EQUALS:
                self.input_text += "+"
            if 0 <= index < 26:
                try:
                    self.input_text += chr(ord("a") + index - 32)
                except Exception: # Handle exceptions in game
                    traceback.print_exc() # Print error to stderr.
            return None
        else: #Need check for valid ascii, index range?
            try:
                self.input_text += chr(ord("a") + index)
            except Exception: # Handle exceptions in game
                traceback.print_exc() # Print error to stderr.
            return None

        return MainGameEventHandler(self.engine)

class SaveGameEventHandler(TextEntryEventHandler):
    def __init__(self, engine: Engine, input_text: str = ""):
        self.engine = engine
        self.input_text = input_text
        self.TITLE = "Enter save game name:"
    """Save in game slot, name text input."""

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        modifier = event.mod
        
        index = key - tcod.event.K_a

        if key == pygame.K_ESCAPE:
            self.engine.message_log.add_message(f"Save game aborted.")
            return MainGameEventHandler(self.engine)
        elif key == pygame.K_RETURN:
            if self.input_text == "":
                self.input_text = "savegame"
            self.engine.message_log.add_message(f"Game saved to {self.input_text}.")
            save_game(self.engine, save_name = self.input_text)
            return MainGameEventHandler(self.engine)
        elif modifier & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT): #Ugly hack, lshift or rshift
            if key == pygame.K_EQUALS:
                self.input_text += "+"
            if 0 <= index < 26:
                try:
                    self.input_text += chr(ord("a") + index - 32)
                except Exception: # Handle exceptions in game
                    traceback.print_exc() # Print error to stderr.
            return None
        else: #Need check for valid ascii, index range?
            try:
                self.input_text += chr(ord("a") + index)
            except Exception: # Handle exceptions in game
                traceback.print_exc() # Print error to stderr.
            return None

        return MainGameEventHandler(self.engine)

class RenameItemEventHandler(InventoryEventHandler):
    """Rename an Item, handy for enchanted gear"""

    TITLE = "Choose an item to rename."

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Return the action for the selected item."""
        
        return None

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        modifier = event.mod
        
        index = key - pygame.K_a
        new_item_name = ""

        if self.engine.enchant_now == True:
            if key != pygame.K_ESCAPE and key != pygame.K_RETURN:
                if modifier & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT): #Ugly hack, lshift or rshift
                    if key == pygame.K_EQUALS:
                            self.engine.enchanting_item.name += "+"
                    if 0 <= index < 26:
                        self.engine.enchanting_item.name = self.engine.enchanting_item.name + chr(ord("a") + index - 32)
                else: #Need check for valid ascii, index range?
                    if index < 1000:
                        self.engine.enchanting_item.name = self.engine.enchanting_item.name + chr(ord("a") + index)
            else:
                self.engine.message_log.add_message(f"Item renaming complete.")
                self.engine.enchant_now = False

        if self.engine.enchant_now == False:
            if 0 <= index <= 26:
                try:
                    selected_item = player.inventory.items[index]
                except IndexError:
                    self.engine.message_log.add_message(f"Invalid entry.", colors.invalid)
                    return None
                self.engine.message_log.add_message(f"Blanking item name.  Enter new name.", colors.white)
                self.engine.enchanting_item = selected_item
                selected_item.name = ""
                self.engine.enchant_now = True

        return super().ev_keydown(event)

class EnchantEventHandler(AskUserEventHandler):
    """This handler enchants items.

    Only at enchanting shops.
    """

    def on_render(self, screen: pygame.display) -> None:
        """Render an inventory menu, which displays the items in the inventory,
        and the letter to select them.  Will move to a different position based
        on where the player is located, so the player can always see where
        they are.
        """
        #super().on_render(screen)
        number_of_items_in_inventory = len(self.engine.player.inventory.items)

        height = number_of_items_in_inventory + 2

        if height <= 3:
            height = 3

        x = 0
        y = 0

        width = 40

        ench_screen = pygame.Surface((width*block_size, height*block_size))
        text_to_screen(ench_screen, text = "Enchanter's Shop", position = (x*block_size, y*block_size))

        if number_of_items_in_inventory > 0:
            for i, item in enumerate(self.engine.player.inventory.items):
                item_key = chr(ord("a") + i)
                equip_status = ""
                num_of_items = ""
                sell_price = int(item.gold_value / 2)
                if item.number_in_stack > 1:
                    num_of_items = f" ({item.number_in_stack})"
                text_to_screen(ench_screen, text = f"({item_key}) {item.name}" + num_of_items + equip_status + f" Sell price: {sell_price} gold.",
                               position = (x*block_size, (y + i + 1)*block_size))
        else:
            text_to_screen(ench_screen, text = " (Empty)", position = (x*block_size, (y + 1)*block_size))
        screen.blit(ench_screen, (0, 0))
        render_bar(screen, self.engine)

        if self.engine.enchant_now == True:
            x2 = 40

            ench_choice = pygame.Surface((40*block_size, 25*block_size))
            text_to_screen(ench_choice, text = "Enchanting Options:", position = (x*block_size, y*block_size))

            enc_item = self.engine.enchanting_item
            mint = enc_item.equippable.enhance_int_bonus
            slot_choices = []

            slot_choices = components.enchanter.enchanter_options(enc_item, enc_item.equippable.slot, slot_choices)

            text_to_screen(ench_choice, text = f"{enc_item.name}, slot: {enc_item.equippable.slot}, list size: {len(slot_choices)}",
                           position = (x*block_size, (y + 20)*block_size))

            y_hold = 1
            text_to_screen(ench_choice, text = f"{enc_item.name}, value: {enc_item.gold_value}",
                           position = (x*block_size, (y + y_hold)*block_size))

            for choices in range(len(slot_choices) - 1):
                y_hold += 1
                letter = chr(ord("a") + choices)
                text_to_screen(ench_choice, text = f"({letter}) to improve {slot_choices[choices + 1][0]} bonus to {slot_choices[choices + 1][2]}: {int(slot_choices[choices + 1][2])**2*slot_choices[choices + 1][4]} gold.",
                               position = (x*block_size, (y + y_hold)*block_size))
            screen.blit(ench_choice, (x2*block_size, 0))
            render_bar(screen, self.engine)

    def ev_keydown(
        self, event: pygame.KeyDown,
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        index = key - pygame.K_a
        test = False
        discount = 0

        enc_item = self.engine.enchanting_item
        slot_choices = []

        if self.engine.enchant_now == True:
            if key == tcod.event.K_ESCAPE:
                self.engine.enchant_now = False
                self.engine.message_log.add_message("Enchant Aborted.", colors.invalid)
                return None
            slot_choices = components.enchanter.enchanter_options(enc_item, enc_item.equippable.slot, slot_choices)
            if slot_choices[index + 1][3] == "square":
                cost = slot_choices[index +1 ][2]**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][3] == "square+2":
                cost = (slot_choices[index + 1][2] + 2)**2*slot_choices[index + 1][4]
            else:
                self.engine.message_log.add_message("Enchant formula not recognized.", colors.invalid)
                self.engine.enchant_now = False
                return None
            if slot_choices[index + 1][0] == "Int":
                discount = enc_item.equippable.enhance_int_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Wis":
                discount = enc_item.equippable.enhance_wis_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Cha":
                discount = enc_item.equippable.enhance_cha_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Str":
                discount = enc_item.equippable.enhance_str_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Dex":
                discount = enc_item.equippable.enhance_dex_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Con":
                discount = enc_item.equippable.enhance_con_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Armor":
                discount = enc_item.equippable.enhance_armor_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Weapon":
                discount = enc_item.equippable.enhance_melee_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Ranged Weapon":
                discount = enc_item.equippable.enhance_ranged_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Shield":
                discount = enc_item.equippable.enhance_shield_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Animated Shield":
                discount = (enc_item.equippable.enhance_shield_bonus + 2)**2*slot_choices[index + 1][4] #Animated costs + 2 bonus
            elif slot_choices[index + 1][0] == "Ring of Protection":
                discount = enc_item.equippable.deflection_bonus**2*slot_choices[index + 1][4]
            elif slot_choices[index + 1][0] == "Amulet of Natural Armor":
                discount = enc_item.equippable.enhance_na_bonus**2*slot_choices[index + 1][4]
            else:
                self.engine.message_log.add_message("Discount option not found.", colors.invalid)
            if player.battler.gold < (cost - discount):
                self.engine.message_log.add_message("You don't have enough gold.", colors.invalid)
            elif discount >= cost:
                self.engine.message_log.add_message("That wouldn't improve the item.", colors.invalid)
            else:
                player.battler.gold -= (cost - discount)
                self.engine.message_log.add_message(f"Your {slot_choices[0][1]} now gives + {slot_choices[index+1][2]} to {slot_choices[index+1][0]}.")
                if slot_choices[index + 1][0] == "Int":
                    enc_item.equippable.enhance_int_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Wis":
                    enc_item.equippable.enhance_wis_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Cha":
                    enc_item.equippable.enhance_cha_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Str":
                    enc_item.equippable.enhance_str_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Dex":
                    enc_item.equippable.enhance_dex_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Con":
                    enc_item.equippable.enhance_con_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Armor":
                    enc_item.equippable.enhance_armor_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Weapon":
                    enc_item.equippable.enhance_melee_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Ranged Weapon":
                    enc_item.equippable.enhance_ranged_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Shield":
                    enc_item.equippable.enhance_shield_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Animated Shield":
                    enc_item.equippable.enhance_shield_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Ring of Protection":
                    enc_item.equippable.deflection_bonus = slot_choices[index + 1][2]
                elif slot_choices[index + 1][0] == "Amulet of Natural Armor":
                    enc_item.equippable.enhance_na_bonus = slot_choices[index + 1][2]
                else:
                    self.engine.message_log.add_message("Enchant option not found.", colors.invalid)
            self.engine.enchant_now = False
            return None

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", colors.invalid)
                return None
            return self.enchant_item(selected_item)
        return super().ev_keydown(event)

    def enchant_item(self, item: Item) -> Optional[Action]:
        """Called when the user selects a valid item."""
        player = self.engine.player
        if item in (player.equipment.main_hand, player.equipment.off_hand, player.equipment.body,
                    player.equipment.neck, player.equipment.ranged, player.equipment.waist,
                    player.equipment.lring, player.equipment.rring, player.equipment.head,
                    player.equipment.cloak, player.equipment.eyes, player.equipment.shirt,
                    player.equipment.wrists, player.equipment.feet, player.equipment.hands,
                    player.equipment.misc):
            self.engine.message_log.add_message("You can't enchant something you are wearing.", colors.white)
        elif item.can_stack == True:
            self.engine.message_log.add_message("The shop has no interest in that item.", colors.white)
        elif item.equippable != None:
            self.engine.enchanting_item = item
            self.engine.message_log.add_message(f"Enchanting item is: {self.engine.enchanting_item.name}")
            self.engine.enchant_now = True
            return None
        else:
            self.engine.message_log.add_message(f"This item is not valid for enchanting.")


class ShopSellEventHandler(AskUserEventHandler):
    """This event sells to a shop."""

    TITLE = "Stuff to sell."

    def on_render(self, screen: pygame.display) -> None:
        """Render an inventory menu, which displays the items in the inventory,
        and the letter to select them.  Will move to a different position based
        on where the player is located, so the player can always see where
        they are.
        """
        #super().on_render(screen)
        number_of_items_in_inventory = len(self.engine.player.inventory.items)

        height = number_of_items_in_inventory + 2

        if height <= 3:
            height = 3

        x = 0
        y = 0

        width = 40

        sell_screen = pygame.Surface((width*block_size, height*block_size))

        if number_of_items_in_inventory > 0:
            for i, item in enumerate(self.engine.player.inventory.items):
                item_key = chr(ord("a") + i)
                equip_status = ""
                num_of_items = ""
                if self.engine.player.equipment.main_hand == item:
                    if self.engine.player.equipment.main_hand.equippable.slot == EquipmentSlots.MAIN_HAND:
                        equip_status = " (in main hand)"
                    elif self.engine.player.equipment.main_hand.equippable.slot == EquipmentSlots.TWO_HAND:
                        equip_status = " (in both hands)"
                elif self.engine.player.equipment.off_hand == item:
                    equip_status = " (on off hand)"
                elif self.engine.player.equipment.body == item:
                    equip_status = " (worn on body)"
                elif self.engine.player.equipment.neck == item:
                    equip_status = " (worn on neck)"
                elif self.engine.player.equipment.ranged == item:
                    equip_status = " (as ranged)"
                elif self.engine.player.equipment.waist == item:
                    equip_status = " (on waist)"
                elif self.engine.player.equipment.lring == item:
                    equip_status = " (on left hand)"
                elif self.engine.player.equipment.rring == item:
                    equip_status = " (on right hand)"
                elif self.engine.player.equipment.head == item:
                    equip_status = " (on head)"
                elif self.engine.player.equipment.cloak == item:
                    equip_status = " (worn on shoulders)"
                elif self.engine.player.equipment.eyes == item:
                    equip_status = " (worn on face)"
                elif self.engine.player.equipment.shirt == item:
                    equip_status = " (worn about torso)"
                elif self.engine.player.equipment.wrists == item:
                    equip_status = " (worn on wrists)"
                elif self.engine.player.equipment.feet == item:
                    equip_status = " (worn on feet)"
                elif self.engine.player.equipment.hands == item:
                    equip_status = " (worn on hands)"
                elif self.engine.player.equipment.misc == item:
                    equip_status =  " (worn slotless)"
                sell_price = int(item.gold_value / 2)
                if item.number_in_stack > 1:
                    num_of_items = f" ({item.number_in_stack})"
                text_to_screen(sell_screen, text = (f"({item_key}) {item.name}" + num_of_items + equip_status + f" Sell price: {sell_price} gold."),
                               position = (x*block_size, (y + i + 1)*block_size))
        else:
            text_to_screen(sell_screen, text = "(Empty)", position = (x*block_size, (y + 1)*block_size))
        screen.blit(sell_screen, (0, 0))
        render_bar(screen, self.engine)

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.key
        index = key - pygame.K_a

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", colors.invalid)
                return None
            return self.sell_item(selected_item)
        return super().ev_keydown(event)

    def sell_item(self, item: Item) -> Optional[Action]:
        """Called when the user selects a valid item."""
        player = self.engine.player
        if item in (player.equipment.main_hand, player.equipment.off_hand, player.equipment.body,
                    player.equipment.neck, player.equipment.ranged, player.equipment.waist,
                    player.equipment.lring, player.equipment.rring, player.equipment.head,
                    player.equipment.cloak, player.equipment.eyes, player.equipment.shirt,
                    player.equipment.wrists, player.equipment.feet, player.equipment.hands,
                    player.equipment.misc):
            self.engine.message_log.add_message("You can't sell something you are wearing.", colors.white)
        elif item.gold_value > 0:
            player.battler.gold += int(item.gold_value / 2)
            self.engine.message_log.add_message(f"You sell the {item.name} for {int(item.gold_value / 2)} gold.", colors.yellow)
            if item.number_in_stack > 1:
                item.number_in_stack -= 1
            else:
                player.inventory.items.remove(item)
        else:
            self.engine.message_log.add_message("The shop has no interest in that item.", colors.white)

class InventoryActivateHandler(InventoryEventHandler):
    """Handle using an inventory item."""

    TITLE = "Select an item to use, letter corresponds to item."

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Return the action for the selected item."""
        if item.consumable:
            return item.consumable.get_action(self.engine.player)
        elif item.equippable:
            return item.equippable.activate(self.engine.player)
        elif isinstance(item, Bag): #item.name == "Red Bag":
            self.engine.enchanting_item = item
            return UseBagHandler(self.engine)

class InventoryDropHandler(InventoryEventHandler):
    """Handle dropping an inventory item."""

    TITLE = "Select an item to drop, letter corresponds to item."

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Drop this item."""
        return actions.DropItem(self.engine.player, item)

class EquipmentHandler(AskUserEventHandler):
    """Handle removing or viewing equipped items."""

    TITLE = "Select an item remove, letter corresponds to item."
            
    def on_render(self, screen: pygame.display) -> None:
        """Render equipment screen.  This displays worn gear,
        and allows the user to remove items.
        """
        #super().on_render(screen)
        equipment_set = ["in main hand", "on off hand", "worn on body", "worn on neck", "as ranged", "on waist", "on left hand", "on right hand",
                     "on head", "worn on shoulders", "worn on eyes", "worn about torso", "worn on wrists", "worn on feet", "worn on hands",
                     "as Animated Shield"]
        """
        gear_list = [f"{self.engine.player.equipment.main_hand.name}", f"{self.engine.player.equipment.off_hand.name}",
                     f"{self.engine.player.equipment.body.name}", f"{self.engine.player.equipment.neck.name}",
                     f"{self.engine.player.equipment.ranged.name}", f"{self.engine.player.equipment.waist.name}",
                     f"{self.engine.player.equipment.lring.name}", f"{self.engine.player.equipment.rring.name}",
                     f"{self.engine.player.equipment.head.name}", f"{self.engine.player.equipment.cloak.name}",
                     f"{self.engine.player.equipment.eyes.name}", f"{self.engine.player.equipment.shirt.name}",
                     f"{self.engine.player.equipment.wrists.name}", f"{self.engine.player.equipment.feet.name}",
                     f"{self.engine.player.equipment.hands.name}", f"{self.engine.player.equipment.misc.name}"]
        """
        check_list = [self.engine.player.equipment.main_hand, self.engine.player.equipment.off_hand,
                     self.engine.player.equipment.body, self.engine.player.equipment.neck,
                     self.engine.player.equipment.ranged, self.engine.player.equipment.waist,
                     self.engine.player.equipment.lring, self.engine.player.equipment.rring,
                     self.engine.player.equipment.head, self.engine.player.equipment.cloak,
                     self.engine.player.equipment.eyes, self.engine.player.equipment.shirt,
                     self.engine.player.equipment.wrists, self.engine.player.equipment.feet,
                     self.engine.player.equipment.hands, self.engine.player.equipment.misc]

        for i, gear in enumerate(equipment_set):
            line = f"[None]"
            if check_list[i] == None:
                line = f"[None] ({equipment_set[i]})"
            else:
                letter = chr(ord("a") + i)
                line = f"({letter})    {check_list[i].name} ({equipment_set[i]})"
            text_to_screen(screen, line, position = (10*16, 16*10+16*i))
        render_bar(screen, self.engine)
        pygame.display.update()
                

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        player = self.engine.player
        button = event.key
        index = button - pygame.K_a

        check_list = [self.engine.player.equipment.main_hand, self.engine.player.equipment.off_hand,
                     self.engine.player.equipment.body, self.engine.player.equipment.neck,
                     self.engine.player.equipment.ranged, self.engine.player.equipment.waist,
                     self.engine.player.equipment.lring, self.engine.player.equipment.rring,
                     self.engine.player.equipment.head, self.engine.player.equipment.cloak,
                     self.engine.player.equipment.eyes, self.engine.player.equipment.shirt,
                     self.engine.player.equipment.wrists, self.engine.player.equipment.feet,
                     self.engine.player.equipment.hands, self.engine.player.equipment.misc]

        if len(check_list) > index >= 0 and check_list[index] != None:
            check_list[index].equippable.activate(self.engine.player)
        if pygame.K_ESCAPE:
            return super().ev_keydown(event)

class SelectIndexHandler(AskUserEventHandler):
    """Handles asking the user for an index on the map."""

    def __init__(self, engine: Engine):
        """Sets the cursor to the player when this handler is constructed."""
        #super().__init__(engine)
        self.engine = engine
        player = self.engine.player
        if self.engine.last_target.is_alive == True and self.engine.game_map.visible[self.engine.last_target.x][self.engine.last_target.y] == True:
            engine.mouse_location = self.engine.last_target.x, self.engine.last_target.y
        else:
            engine.mouse_location = player.x, player.y
            engine.last_target = player

    def on_render(self, screen: pygame.display) -> None:
        """Highlight the tile under the cursor."""
        pass

    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        """Check for key movement or confirmation keys."""
        key = event.key
        if key in MOVE_KEYS:
            modifier = 1 # Holding modifier keys will speed up key movement.
            if event.mod & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT):
                modifier *= 5
            if event.mod & (pygame.KMOD_LCTRL | pygame.KMOD_RCTRL):
                modifier *= 10
            if event.mod & (pygame.KMOD_LALT | pygame.KMOD_RALT):
                modifier *= 20

            x, y = self.engine.mouse_location
            dx, dy = MOVE_KEYS[key]
            x += dx * modifier
            y += dy * modifier
            # Clamp the cursor index to the map size.
            x = max(0, min(x, self.engine.game_map.width - 1))
            y = max(0, min(y, self.engine.game_map.height - 1))
            self.engine.mouse_location = x, y
            self.engine.target_location = x, y
            return None
        elif key in CONFIRM_KEYS:
            return self.on_index_selected(*self.engine.mouse_location)
        return super().ev_keydown(event)

    def ev_mousebuttondown(
        self, event: pygame.MOUSEBUTTONDOWN
        ) -> Optional[ActionOrHandler]:
        "Left click confirms a selction."""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        grid_x = int(mouse_x/block_size)
        grid_y = int(mouse_y/block_size)
        self.engine.mouse_location = (grid_x, grid_y)
        if self.engine.game_map.in_bounds(*self.engine.mouse_location):
            return self.on_index_selected(*self.engine.mouse_location)
        return super().ev_mousebuttondown(event)

    def ev_mousemotion(self, event: pygame.MouseMotion) -> None:
        (x_raw, y_raw) = pygame.mouse.get_pos()
        self.engine.mouse_location = (int(x_raw/block_size),  int(y_raw/block_size))
        pygame.display.update()

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Called when an index is selected."""
        raise NotImplementedError()

class SelectMonsterHandler(SelectIndexHandler):
    """Rapidly target monsters.  Cone by arrow/number, closest first.."""

    def __init__(self, engine: Engine):
        """Sets the cursor to the player when this handler is constructed."""
        #super().__init__(engine)
        player = self.engine.player
        if self.engine.last_target.is_alive == True and self.engine.game_map.visible[self.engine.last_target.x][self.engine.last_target.y] == True:
            engine.mouse_location = self.engine.last_target.x, self.engine.last_target.y # If alive and visible, target last opponent.
            engine.target_location = self.engine.last_target.x, self.engine.last_target.y
        else: # Without this check you can target around corners.  If not visible, reset to player so you can't.
            engine.mouse_location = player.x, player.y
            engine.target_location = player.x, player.y

    def on_render(self, screen: pygame.display) -> None:
        """Highlight the tile under the cursor."""
        pass
        
    def ev_keydown(
        self, event: pygame.KeyDown
        ) -> Optional[ActionOrHandler]:
        """Check for key movement or confirmation keys."""
        key = event.key
        NSEW_KEYS = (pygame.K_UP, pygame.K_KP_8, pygame.K_DOWN, pygame.K_KP_2,
                     pygame.K_LEFT, pygame.K_KP_4, pygame.K_RIGHT, pygame.K_KP_6)

        quick_list = []
        dist_list = []
        player = self.engine.player
        lastkey = self.engine.last_keypress
        num_times_pressed = self.engine.num_pressed
        
        if key in NSEW_KEYS:
            if lastkey == "None":
                x, y = player.x, player.y
            """Checks for monsters in cone for cardinal directions: N, S, E, W."""
            if key in (pygame.K_UP, pygame.K_KP_8):
                if lastkey == "Up":
                    self.engine.num_pressed += 1
                else:
                    self.engine.num_pressed = 0
                self.engine.last_keypress = "Up"
                for monster in self.engine.game_map.actors:
                    if monster.y < self.engine.player.y:
                        if self.engine.game_map.visible[monster.x, monster.y]:
                            if abs(monster.y - player.y) >= abs(monster.x - player.x):
                                quick_list.append(monster)
            elif key in (pygame.K_DOWN, pygame.K_KP_2):
                if lastkey == "Down":
                    self.engine.num_pressed += 1
                else:
                    self.engine.num_pressed = 0
                self.engine.last_keypress = "Down"
                for monster in self.engine.game_map.actors:
                    if monster.y > self.engine.player.y:
                        if self.engine.game_map.visible[monster.x, monster.y]:
                            if abs(monster.y - player.y) >= abs(monster.x - player.x):
                                quick_list.append(monster)
            elif key in (pygame.K_LEFT, pygame.K_KP_4):
                if lastkey == "Left":
                    self.engine.num_pressed += 1
                else:
                    self.engine.num_pressed = 0
                self.engine.last_keypress = "Left"
                for monster in self.engine.game_map.actors:
                    if monster.x < self.engine.player.x:
                        if self.engine.game_map.visible[monster.x, monster.y]:
                            if abs(monster.y - player.y) <= abs(monster.x - player.x):
                                quick_list.append(monster)             
            elif key in (pygame.K_RIGHT, pygame.K_KP_6):
                if lastkey == "Right":
                    self.engine.num_pressed += 1
                else:
                    self.engine.num_pressed = 0
                self.engine.last_keypress = "Right"
                for monster in self.engine.game_map.actors:
                    if monster.x > self.engine.player.x:
                        if self.engine.game_map.visible[monster.x, monster.y]:
                            if abs(monster.y - player.y) <= abs(monster.x - player.x):
                                quick_list.append(monster)
            """Sort by distance, closest first."""
            for monster in quick_list:
                dist = math.sqrt((player.x - monster.x)**2 + (player.y - monster.y)**2)
                dist_list.append([dist, monster])
            dist_list = sorted(dist_list, key=lambda x: x[0])
            if dist_list:
                if self.engine.num_pressed > len(dist_list) - 1:
                    self.engine.num_pressed = 0
                    self.engine.last_keypress = "None"                
                target = dist_list[self.engine.num_pressed][1]
                x, y = target.x, target.y
            else:
                x, y = player.x, player.y
                    
            x = max(0, min(x, self.engine.game_map.width - 1))
            y = max(0, min(y, self.engine.game_map.height - 1))
            self.engine.target_location = x, y
            return None
        
        if key in CONFIRM_KEYS:
            return self.on_index_selected(*self.engine.target_location)
        return super().ev_keydown(event)

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Called when an index is selected."""
        raise NotImplementedError()


class ThrowShootEventHandler(SelectMonsterHandler):
    """Throws or Shoots at target selected by keyboard or mouse."""

    def __init__(
        self, engine: Engine, callback: Callable[[Tuple[int, int]],
                                                 Optional[ActionOrHandler]]
    ):
        #super().__init__(engine)
        self.engine = engine
        self.callback = callback

    def on_index_selected(self, x: int, y: int) -> RangedAction:
        return self.callback((x, y))

class LookHandler(SelectIndexHandler):
    "Lets the player look around using the keyboard."""

    def on_index_selected(self, x: int, y: int) -> None:
        """Return to main handler."""
        return MainGameEventHandler(self.engine)

class SingleMeleeAttackHandler(SelectIndexHandler):
    "Handles targeting a single melee enemy."

    def __init__(
        self,
        engine: Engine,
        callback: Callable[[Tuple[int, int]], Optional[ActionOrHandler]]
    ):
        #super().__init__(engine)
        self.engine = engine
        self.callback = callback

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        return self.callback((x, y))

class SingleRangedAttackHandler(SelectMonsterHandler):
    """Handles targeting a single enemy.  Only the enemy selected will be affected."""

    def __init__(
        self,
        engine: Engine,
        callback: Callable[[Tuple[int, int]], Optional[ActionOrHandler]]
    ):
        #super().__init__(engine)
        self.engine = engine
        self.callback = callback

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        return self.callback((x, y))

class ConeAreaAttackHandler(SelectIndexHandler):
    """
    Targets Cone in direction from player
    Cardinal directions
    """
    def __init__(
        self,
        engine: Engine,
        callback: Callable[[Tuple[int, int]], Optional[ActionOrHandler]],
        radius: int = 3,
    ):
        #super().__init__(engine)
        self.engine = engine
        self.radius = radius
        self.callback = callback

    def on_render(self, screen: pygame.display, mouse_target: bool = False) -> None:
        """Highlight the tile under the cursor."""
        #super().on_render(screen)
        self.mouse_target = mouse_target
        self.engine.render_target_cone(screen, self.mouse_target, radius = 3)
        # Draw a cone in cardinal direction
        render_bar(screen, self.engine)
        #Need to add cone code

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        return self.callback((x, y))

class AreaRangedAttackHandler(SelectIndexHandler):
    """
    Handles targeting an area with a given radious.
    Any entity within the area will be affected.
    """
    def __init__(
        self,
        engine: Engine,
        radius: int,
        callback: Callable[[Tuple[int, int]], Optional[ActionOrHandler]],
    ):
        #super().__init__(engine)
        self.engine = engine
        self.radius = radius
        self.callback = callback

    def on_render(self, screen: pygame.display) -> None:
        """Highlight the tile under the cursor."""
        #super().on_render(screen)

        x, y = self.engine.mouse_location

        # Draw a rectangle around the targeted area, so the player
        # can see the affected tiles

        render_bar(screen, self.engine)
        #Need to add rectangle/circle code

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        return self.callback((x, y))

class SummonMonsterHandler(SelectIndexHandler):
    """
    Handles targeting a square to summon a monster.
    """

    def __init__(
        self,
        engine: Engine,
        callback: Callable[[Tuple[int, int]], Optional[ActionOrHandler]],
        radius: int = 0,
    ):
        #super().__init__(engine)
        self.engine = engine
        self.radius = radius
        self.callback = callback

    def on_render(self, screen: pygame.display) -> None:
        """Highlight the tile under the cursor."""
        #super().on_render(screen)

        x, y = self.engine.mouse_location

        # Draw a rectangle around the targeted area, so the player
        # can see the affected tiles

        render_bar(screen, self.engine)
        #Need to add square code

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        return self.callback((x, y))
    
class TakeStairsHandler(EventHandler):
    #Takes stairs, up or down, generating new level.
    #No longer implements, see Actions
    
    def ___init__(
        self,
        engine: Engine,
    ):
        constants = get_constants()
        for entity in self.engine.game_map.entities:
            if (entity.stairs and entity.x == self.engine.player.x and entity.y == self.engine.player.y):
                self.engine.game_map = generate_dungeon(
                    max_rooms = constants['max_rooms'],
                    room_min_size = constants['room_min_size'],
                    room_max_size = constants['room_max_size'],
                    map_width = constants['map_width'],
                    map_height = constants['map_height'],
                    dungeon_level = self.engine.game_map.dungeon_level + entity.stairs.stairs,
                    engine = self.engine,
                )
            return MainGameEventHandler(self.engine)
        self.engine.message_log.add_message("There are no stairs here.", colors.white)
        return MainGameEventHandler(self.engine)

