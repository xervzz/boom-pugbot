# resources.py

from aiohttp import ClientSession


class Sessions:
    requests: ClientSession


class Config:
    discord_token: str
    prefixes: list
    main_guild: int
    web_panel: str
    api_url: str
    lang: str
    game_mode_comp_value: int
    game_mode_wing_value: int
    get5_comp_cfg: str
    get5_wing_cfg: str
