from __future__ import annotations

from typing import TYPE_CHECKING

from tcod.console import Console
from tcod.map import compute_fov
import pygame

import exceptions
import message_log
from render_functions import render_bar, render_names_at_mouse_location
from loader_functions.initialize_new_game import get_constants

if TYPE_CHECKING:
    from entity import Actor, Item
    from game_map import GameMap, GameWorld

constants = get_constants()
block_size = constants['block_size']

class Engine:
    game_map: GameMap
    game_world: GameWorld
    
    def __init__(self, player: Actor):
        self.message_log = message_log.MessageLog()
        self.mouse_location = (0, 0)
        self.target_location = (0, 0)
        self.player = player
        self.screen_reset = False
        self.enchant_now = False
        self.enchanting_item: Item = None
        self.last_keypress: str = "None"
        self.num_pressed: int = 0
        self.last_target = player
        self.last_level: int = 0
        self.current_turn: int = 0

    def handle_enemy_turns(self) -> None:
        for entity in set(self.game_map.actors) - {self.player}:
            if entity.ai:
                try:
                    entity.ai.perform()
                except exceptions.Impossible:
                    pass # Ignore impossible action exceptions from AI.

    def update_fov(self) -> None:
        """Recompute the visible area based on the players point of view."""
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles["transparent"],
            (self.player.x, self.player.y),
            radius = 12,
        )
        # If a tile is "visible" it should be added to "explored".
        self.game_map.explored |= self.game_map.visible

    def render(self, screen: pygame.display) -> None:
        self.game_map.render(screen)

        self.message_log.render_messages(screen = screen, x = 40, y = 44, width = 40, height = 5, messages = self.message_log.messages)

        render_bar(main_screen = screen, engine = self)

        render_names_at_mouse_location(screen = screen, x = 25, y = constants['screen_height'] - constants['message_height'] - 1, engine = self)

    def render_target_square(self, screen: pygame.display, mouse_target: bool = False) -> None:
        if mouse_target == True:
            x, y = self.mouse_location
        else:
            x, y = self.target_location
        square_image = pygame.Surface((block_size, block_size))
        square_image.fill((255, 255, 255))
        pygame.draw.rect(square_image, (255, 0, 0), pygame.Rect(0, 0, 16, 16), 2)
        square_image.set_colorkey((255, 255, 255))
        pygame.display.update()
        if self.game_map.in_bounds(x, y):
            screen.blit(square_image, (x*block_size, y*block_size))

    def render_target_cone(self, screen: pygame.display, mouse_target: bool = False, radius: int = 3) -> None:
        if mouse_target == True:
            x, y = self.mouse_location
        else:
            x, y = self.target_location
        player = self.player
        cone_image = pygame.Surface((radius*block_size, radius*block_size))
        cone_image.fill((255, 255, 255))
        cone_image.set_colorkey((255, 255, 255))
        x_offset = 0 # These need to be keyed to radius, currently only for 3
        y_offset = 0
        if x - player.x > 0: # target east of player
            x_offset = 1
            y_offset = -1
            if y - player.y > 0: # target south of player
                y_offset += 2
                pygame.draw.polygon(cone_image, (255, 0, 0), [(0, 0), (radius*block_size, 0), (0, radius*block_size - 2)], 2)
            elif y - player.y < 0: # target north of player
                y_offset -= 2
                pygame.draw.polygon(cone_image, (255, 0, 0), [(0, radius*block_size - 2), (0, 0), (radius*block_size, radius*block_size - 2)], 2)
            else: # target directly east
                pygame.draw.polygon(cone_image, (255, 0, 0), [(0, int(radius*block_size/2)), (radius*block_size, radius*block_size - 2), (radius*block_size, 0)], 2)
        elif x - player.x < 0: # target west of player
            x_offset = - 3
            y_offset = - 1
            if y - player.y < 0: # target north of player
                y_offset -= 2
                pygame.draw.polygon(cone_image, (255, 0, 0), [(radius*block_size - 2, radius*block_size - 2), (0, radius*block_size - 2), (radius*block_size - 2, 0)], 2)
            elif y - player.y > 0: # target south of player
                y_offset += 2
                pygame.draw.polygon(cone_image, (255, 0, 0), [(0, 0), (radius*block_size - 2, radius*block_size - 2), (radius*block_size - 2, 0)], 2)
            else: # target direct west
                pygame.draw.polygon(cone_image, (255, 0, 0), [(radius*block_size, int(radius*block_size/2)), (0, radius*block_size - 2), (0, 0)], 2)
        elif y - player.y > 0: # target directly south of the player
            y_offset = 1
            x_offset = - 1
            pygame.draw.polygon(cone_image, (255, 0, 0), [(int(radius*block_size/2), 0), (0, radius*block_size - 2), (radius*block_size, radius*block_size)], 2)
        elif y - player.y < 0: # target directly north of the player
            y_offset = - 3
            x_offset = - 1
            pygame.draw.polygon(cone_image, (255, 0, 0), [(int(radius*block_size/2), radius*block_size), (radius*block_size, 0), (0, 0)], 2)
        else: # target on player
            pass
        screen.blit(cone_image, ((player.x + x_offset)*block_size, (player.y + y_offset)*block_size))
        pygame.display.update()
