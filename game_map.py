from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING

import numpy as np # type: ignore
from tcod.console import Console

from entity import Actor, Item, Gold, Shop, Enchant, Stairs
import tile_types
import ptile_type
import render_functions
from loader_functions.initialize_new_game import get_constants

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

constants = get_constants()
block_size = constants['block_size']

class GameMap:
    def __init__(
        self,
        engine: Engine,
        width: int,
        height: int,
        dungeon_level: int,
        entities: Iterable[Entity] = (),
        stairs: int = 1,
    ):
        self.engine = engine
        self.width, self.height = width, height
        self.entities = set(entities)
        self.tiles = np.full((width, height), fill_value = tile_types.wall, order = "F")

        self.dungeon_level = dungeon_level
        self.stairs = stairs

        self.visible = np.full(
            (width, height), fill_value = False, order = "F"
        ) # Tiles the player can currently see.
        self.explored = np.full(
            (width, height), fill_value = False, order = "F"
        ) # Tiles the player has seen before.

    @property
    def gamemap(self) -> GameMap:
        return self

    @property
    def actors(self) -> Iterator[Actor]:
        """Iterate over this maps living actors."""
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Actor) and entity.is_alive
        )

    @property
    def items(self) -> Iterator[Item]:
        yield from (entity for entity in self.entities if isinstance(entity, Item))

    @property
    def gold_piles(self) -> Iterator[Gold]:
        yield from (entity for entity in self.entities if isinstance(entity, Gold))

    @property
    def shops(self) -> Iterator[Shop]:
        yield from (entity for entity in self.entities if isinstance(entity, Shop))

    @property
    def enchant(self) -> Iterator[Enchant]:
        yield from (entity for entity in self.entities if isinstance(entity, Enchant))

    @property
    def stairs_iter(self) -> Iterator[Stairs]:
        yield from (entity for entity in self.entities if isinstance(entity, Stairs))

    def get_blocking_entity_at_location(
        self, location_x: int, location_y: int,
    ) -> Optional[Entity]:
        for entity in self.entities:
            if (
                entity.blocks_movement
                and entity.x == location_x
                and entity.y == location_y
            ):
                return entity
            
        return None

    def get_actor_at_location(self, x: int, y: int) -> Optional[Actor]:
        for actor in self.actors:
            if actor.x == x and actor.y == y:
                return actor

        return None

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if x and y are inside of the bounds of this map."""
        return 0 <= x < self.width and 0 <= y < self.height

    def render(self, screen: pygame.display) -> None:
        """
        Renders the map.

        If a tile is in the "visible" array, then draw it with the "light" colors.
        If it isn't, but it's in the "explored" array, then draw it with the "dark" colors.
        Otherwise, the default is "SHROUD".
        """

        """
        self.tiles[0 : self.width, 0 : self.height] = np.select(
            condlist=[self.visible, self.explored],
            choicelist=[self.tiles["light"], self.tiles["dark"]],
            default=ptile_type.SHROUD
        )
        """
        ch_floor = ptile_type.floors
        ch_wall = ptile_type.walls
        ch_tile = ptile_type.tiles
        for i in range(self.width):
            for j in range(self.height):
                if self.visible[i][j]:
                    if self.tiles[i, j] == tile_types.floor:
                        screen.blit(ch_floor, (i*block_size, j*block_size), (64, 64, 16, 16))
                    else:
                        screen.blit(ch_wall, (i*block_size, j*block_size), (3*16, 18*16, 16, 16))
                elif self.explored[i][j]:
                    if self.tiles[i, j] == tile_types.floor:
                        screen.blit(ch_floor, (i*block_size, j*block_size), (9*16, 0, 16, 16))
                        screen.blit(ch_floor, (i*block_size, j*block_size), (4*16, 13*16, 16, 16))
                    else:
                        screen.blit(ch_wall, (i*block_size, j*block_size), (8*16, 0, 16, 16))
                        screen.blit(ch_wall, (i*block_size, j*block_size), (3*16, 24*16, 16, 16))
                else:
                    screen.blit(ch_tile, (i*block_size, j*block_size), (0, 32, 16, 16))
                #screen.blit(ptile_type.floors, (i*block_size, j*block_size), (choice[2][0][0], choice[2][0][1], choice[2][1][0], choice[2][1][1]))
        """
        console.tiles_rgb[0 : self.width, 0 : self.height] = 10150, [255, 255, 0], [0, 0, 0]
        """
        entities_sorted_for_rendering = sorted(
            self.entities, key = lambda x: x.render_order.value
        )
        
        for entity in entities_sorted_for_rendering:
            # Only print entities that are in the FOV, or previously seen stairs and shops.
            if self.visible[entity.x, entity.y] or ((entity in self.stairs_iter or entity in self.shops) and self.explored[entity.x, entity.y]):
                render_functions.draw_entity(screen, entity)
            else:
                pass

class GameWorld:
    """
    Holds the settings for the GameMap, and generates new maps when moving down the stairs.
    """

    def __init__(
        self,
        *,
        engine: Engine,
        map_width: int,
        map_height: int,
        max_rooms: int,
        room_min_size: int,
        room_max_size: int,
        current_floor: int = 0
    ):
        self.engine = engine

        self.map_width = map_width
        self.map_height = map_height

        self.max_rooms = max_rooms

        self.room_min_size = room_min_size
        self.room_max_size = room_max_size

        self.current_floor = current_floor

    def generate_floor(self, stairs: int = 0) -> None:
        from procgen import generate_dungeon, generate_town

        self.stairs = stairs
        self.current_floor = self.engine.game_map.dungeon_level
        self.current_floor += self.stairs

        if self.current_floor == 0:
            self.engine.game_map = generate_town(
                engine = self.engine,
                max_rooms=self.max_rooms,
                room_min_size=self.room_min_size,
                room_max_size=self.room_max_size,
                map_width=self.map_width,
                map_height=self.map_height,
                dungeon_level = self.current_floor
            )
        else:
            self.engine.game_map = generate_dungeon(
                max_rooms=self.max_rooms,
                room_min_size=self.room_min_size,
                room_max_size=self.room_max_size,
                map_width=self.map_width,
                map_height=self.map_height,
                engine=self.engine,
                dungeon_level = self.current_floor,
                stairs = self.stairs
            )
