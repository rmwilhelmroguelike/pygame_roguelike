from typing import Tuple
import pygame
import os

import numpy as np # type: ignore

# Tile graphics structured type compatible with Console.tiles_rgb.
graphic_dt = np.dtype(
    [
        ("ch", np.int32), # Unicode codepoint.
        ("fg", "3B"), # 3  unsigned bytes, for RGB colors.
        ("bg", "3B"),
    ]
)

class pgraphic_dt():
    def __init__(self, xpos:int = 0, ypos:int  = 0, xsize:int = 0, ysize:int = 0):
        self.xpos = xpos
        self.ypos = ypos
        self.xsize = xsize
        self.ysize = ysize
        return Tuple[Tuple[self.xpos, self.ypos],Tuple[self.xsize, self.ysize]]

# Tile struct used for statically defined tile data.
tile_dt = np.dtype(
    [
        ("walkable", np.bool), # True if this tile can be walked over.
        ("transparent", np.bool), # True if this tile doesn't block FOV.
        ("dark", pgraphic_dt), # Graphics for when this tile is not in FOV.
        ("light", pgraphic_dt), # Graphics for when this tile is in FOV.
    ]
)

walls = pygame.image.load(os.path.join('Dawnlike', 'Objects', 'Wall.png'))
#walls.convert()
floors = pygame.image.load(os.path.join('Dawnlike', 'Objects', 'Floor.png'))
#floors.convert()
tiles = pygame.image.load(os.path.join('Dawnlike', 'Objects', 'Tile.png'))

def new_ptile(
    *,
    walkable: int,
    transparent: int,
    dark: pgraphic_dt,
    light: pgraphic_dt,
    graphic: pygame.Surface,
) -> np.ndarray:
    """Helper function for defining individual tile types """
    return np.array((walkable, transparent, dark, light), dtype = tile_dt)

SHROUD = new_ptile(
    walkable = False,
    transparent = False,
    dark = ((0, 304), (16, 16)),
    light = ((0, 96), (16, 16)),
    graphic = floors,
)

floor = new_ptile(
    walkable = True,
    transparent = True,
    dark = ((0, 0), (16, 16)),
    light = ((16, 16), (16, 16)),
    graphic = floors,
)
wall = new_ptile(
    walkable = False,
    transparent = False,
    dark = ((0, 304), (16, 16)),
    light = ((0, 96), (16, 16)),
    graphic = walls,
)
