from __future__ import annotations

from typing import TYPE_CHECKING

import colors
import pygame
import traceback
import os
from loader_functions.initialize_new_game import get_constants

if TYPE_CHECKING:
    from tcod import Console
    from engine import Engine
    from game_map import GameMap

constants = get_constants()
block_size = constants['block_size']

def text_to_screen(screen, text = '', color = colors.white, size = 16, position = (0, 0), font = 'arial'):
    font = pygame.font.SysFont(font, size)
    image = font.render(text, True, color)
    screen.blit(image, position)

def get_names_at_location(x: int, y: int, game_map: GameMap) -> str:
    if not game_map.in_bounds(x, y) or not game_map.visible[x, y]:
        return ""

    names = ", ".join(
        entity.name for entity in game_map.entities if entity.x == x and entity.y == y
    )

    return names.capitalize()

def render_bar(main_screen: pygame.display, engine: Engine) -> None:
    
    current_mana = engine.player.battler.mana
    maximum_mana = engine.player.battler.max_mana
    current_hp = engine.player.battler.hp
    maximum_hp = engine.player.battler.max_hp
    total_width = constants['bar_width']
    dungeon_level = engine.game_map.dungeon_level
    xp = engine.player.level.current_xp
    xp_to_level = engine.player.level.experience_to_next_level
    player_level = engine.player.level.current_level
    player_gold = engine.player.battler.gold
    game_turn = engine.current_turn
    height = 6
    bar_surf = pygame.Surface((total_width*block_size, height*block_size))

    if (maximum_mana > 0) and (current_mana < 10000):
        percent_full = int(100*current_mana/maximum_mana)
        percent_empty = 100 - percent_full
        if int(percent_empty*total_width/100) > 0:
            mana_empty_surf = pygame.Surface((int(percent_empty*total_width/100)*block_size, block_size))
            mana_empty_surf.fill(colors.bar_empty)
            bar_surf.blit(mana_empty_surf, ((int(percent_full*total_width)*block_size, block_size)))
        mana_full_surf = pygame.Surface((int(percent_full*total_width/100)*block_size, block_size))
        mana_full_surf.fill(colors.bar_filled)
        bar_surf.blit(mana_full_surf, ((0*block_size, 0*block_size)))
        text_to_screen(bar_surf, text = f"MANA: {current_mana}/{maximum_mana}",
                       position = (0*block_size, 0*block_size))

    hp_percent_full = int(total_width*current_hp / maximum_hp)
    hp_percent_empty = total_width - hp_percent_full
    if hp_percent_full > 0:
        hp_full_surf = pygame.Surface((hp_percent_full*block_size, block_size))
        hp_full_surf.fill(colors.bar_filled)
        bar_surf.blit(hp_full_surf, (0*block_size, block_size))
    if hp_percent_empty > 0:
        hp_empty_surf = pygame.Surface((hp_percent_empty*block_size, block_size))
        hp_empty_surf.fill(colors.bar_empty)
        bar_surf.blit(hp_empty_surf, (hp_percent_full*block_size, block_size))
    text_to_screen(bar_surf, text = f"HP: {current_hp}/{maximum_hp}", position = (0*block_size, 1*block_size))

    text_to_screen(bar_surf, text = f"Dungeon: {dungeon_level}, Player: {player_level}",
                   position = (0*block_size, 2*block_size))
    text_to_screen(bar_surf, text = f"Current xp: {xp}/{xp_to_level}",
                   position = (0*block_size, 3*block_size))
    text_to_screen(bar_surf, text = f"Turn: {game_turn}", position = (0*block_size, 4*block_size))
    text_to_screen(bar_surf, text = f"Player Gold: ${player_gold}", position = (0*block_size, 5*block_size))
    main_screen.blit(bar_surf, (0, 44*block_size))

def render_names_at_mouse_location(
    screen: pygame.display, x: int, y: int, engine: Engine
) -> None:
    mouse_x, mouse_y = pygame.mouse.get_pos()
    grid_x = int(mouse_x/block_size)
    grid_y = int(mouse_y/block_size)

    names_at_mouse_location = get_names_at_location(
        x = grid_x, y = grid_y, game_map = engine.game_map
    )
    name_bar = pygame.Surface((30*block_size, block_size))
    text_to_screen(name_bar, text = names_at_mouse_location, position = (0*block_size, 0*block_size))
    screen.blit(name_bar, ((x*block_size, y*block_size)))

def render_names_at_target_location(
    screen: pygame.display, x: int, y: int, engine: Engine
) -> None:
    names_at_target_location = get_names_at_location(
        x = engine.target_location[0], y = engine.target_location[1],
        game_map = engine.game_map
    )
    name_bar = pygame.Surface((30*block_size, block_size))
    text_to_screen(name_bar, text = names_at_target_location, position = (0*block_size, 0*block_size))
    screen.blit(name_bar, ((x*block_size, y*block_size)))

def to_pixel(block_num):
    return block_num * block_size

def draw_entity(screen, entity):
    try:
        image = pygame.image.load(entity.graphic)
    except Exception:
        traceback.print_exc()
        print(entity.name)
        image = pygame.image.load(os.path.join('Dawnlike', 'Characters', 'Player1.png'))
    pos = entity.graphic_pos
    screen.blit(image, (to_pixel(entity.x), to_pixel(entity.y)), (pos[0], pos[1], block_size, block_size))
