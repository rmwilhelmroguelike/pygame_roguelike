import os

import shelve
import pickle
import copy

def save_game(engine, save_name: str = 'savegame'):
    with shelve.open(save_name, 'n') as data_file:
        data_file['engine'] = engine
        data_file['player'] = engine.player
        data_file['game_map'] = engine.game_map
        data_file.close()

def load_game(save_name: str = 'savegame'):
    if not os.path.isfile('savegame.dat'):
        raise FileNotFoundError

    with shelve.open(save_name, 'r') as data_file:
        engine = data_file['engine']
        player = data_file['player']
        game_map = data_file['game_map']
        data_file.close()

    return engine
