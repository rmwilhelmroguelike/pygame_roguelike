#!/usr/bin/env python3
#import copy
import traceback

import tcod
import tcod.event
import pygame

from typing import Iterable, Iterator
import colors
import entity_factories
import exceptions
import input_handlers
from loader_functions.initialize_new_game import get_constants # get_game_variables
from loader_functions.player_init import get_player
from input_handlers import MainGameEventHandler, TownPortalEventHandler, SelectMonsterHandler, SummonMonsterHandler, SelectIndexHandler, ConeAreaAttackHandler
import setup_game
import render_functions


constants = get_constants()
block_size = constants['block_size']

    # Numpad keys.
MOVE_KEYS = {
    pygame.K_KP_1: (-1, 1),
    pygame.K_KP_2: (0, 1),
    pygame.K_KP_3: (1, 1),
    pygame.K_KP_4: (-1, 0),
    pygame.K_KP_6: (1, 0),
    pygame.K_KP_7: (-1, -1),
    pygame.K_KP_8: (0, -1),
    pygame.K_KP_9: (1, -1),
}

def to_pixel(block_num):
    return block_num * block_size

def is_square_handler(handler):
    if isinstance(handler, input_handlers.SelectMonsterHandler):
        return True
    elif isinstance(handler, input_handlers.SummonMonsterHandler):
        return True
    elif isinstance(handler, input_handlers.SelectIndexHandler):
        return True
    else:
        return False
    

def main() -> None:

    pygame.init()

    player_x = int(constants['screen_width']*block_size/2)
    player_y = int(constants['screen_height']*block_size/2)

    size = (to_pixel(constants['screen_width']), to_pixel(constants['screen_height']))
    window = pygame.display.set_mode(size)
    start_event = pygame.event.poll()
    handler: input_handlers.BaseEventHandler = input_handlers.MainMenu()
    handler.on_render(window)
    handler = handler.handle_events(start_event)
    #handler.state = handler
    pygame.display.set_caption("Second try roguelike")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                try:
                    if isinstance(handler, input_handlers.BaseEventHandler):
                        handler = handler.handle_events(event) #Is handler
                        if isinstance(handler, input_handlers.MainGameEventHandler):
                            handler.engine.render(window)
                        elif isinstance(handler, input_handlers.ConeAreaAttackHandler):
                            handler.engine.render(window)
                            handler.on_render(window, mouse_target = False)
                        elif is_square_handler(handler): #could alter on_render for all this
                            handler.engine.render(window)
                            handler.engine.render_target_square(window, mouse_target = False)
                            render_functions.render_names_at_target_location(
                                screen = window, x = 25, y = constants['screen_height'] - constants['message_height'] - 1,
                                engine = handler.engine)
                        else:
                            handler.on_render(window)
                            if not isinstance(handler, input_handlers.MainMenu): #Clumsy.  MainMenu doesn't have engine defined
                                handler.engine.message_log.render_messages(screen = window, #Needed so message are visible
                                        x = 40, y = 44, width = 40, height = 5,
                                        messages = handler.engine.message_log.messages)
                    else: #Is action
                        handler.perform()
                        handler = MainGameEventHandler(handler.engine) #Actions always return to MainGame
                        handler.engine.update_fov()
                        handler.engine.render(window)
                except Exception: # Handle exceptions in game
                    traceback.print_exc() # Print error to stderr.
                    # The print the error to the message
            elif event.type == pygame.MOUSEMOTION and isinstance(handler, input_handlers.MainGameEventHandler):
                handler.ev_mousemotion(event)
                handler.engine.render(window)
            elif event.type == pygame.MOUSEMOTION and isinstance(handler, input_handlers.ConeAreaAttackHandler):
                handler = handler.handle_events(event)
                handler.engine.render(window)
                handler.on_render(window, True)
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION) and is_square_handler(handler):
                handler = handler.handle_events(event)
                handler.engine.render(window)
                handler.engine.render_target_square(window, mouse_target = True)
            pygame.display.update()
            pygame.event.pump()
        
    pygame.quit()

if __name__ == "__main__":
    main()
