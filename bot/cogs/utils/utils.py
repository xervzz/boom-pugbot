# utils.py

import os
import json
import math
from dotenv import load_dotenv

import discord
from bot.resources import Config


FLAG_CODES = {
    '🇩🇿': 'DZ', '🇦🇷': 'AR', '🇦🇺': 'AU', '🇦🇹': 'AT', '🇦🇿': 'AZ', '🇧🇪': 'BE', '🇧🇷': 'BR',
    '🇧🇬': 'BG', '🇨🇦': 'CA', '🇷🇴': 'RO', '🇨🇳': 'CN', '🇨🇮': 'CI', '🇭🇷': 'HR', '🇰🇼': 'KW',
    '🇨🇿': 'CZ', '🇩🇰': 'DK', '🇪🇬': 'EG', '🇫🇴': 'FO', '🇫🇮': 'FI', '🇫🇷': 'FR', '🇩🇪': 'DE', '🇬🇷': 'GR',
    '🇭🇺': 'HU', '🇮🇸': 'IS', '🇮🇳': 'IN', '🇮🇶': 'IQ', '🇮🇪': 'IE', '🇮🇱': 'IL', '🇯🇵': 'JP', '🇯🇴': 'JO',
    '🇱🇧': 'LB', '🇱🇾': 'LY', '🇲🇦': 'MA', '🇳🇿': 'NZ', '🇳🇴': 'NO', '🇵🇸': 'PS', '🇵🇱': 'PL', '🇵🇹': 'PT',
    '🇶🇦': 'QA', '🇷🇺': 'RU', '🇸🇦': 'SA', '🇸🇰': 'SK', '🇸🇮': 'SI', '🇰🇷': 'KR', '🇪🇸': 'ES', '🇺🇾': 'UY',
    '🇸🇩': 'SD', '🇸🇪': 'SE', '🇨🇭': 'CH', '🇸🇾': 'SY', '🇾🇪': 'YE', '🇺🇳': 'UN', '🇺🇸': 'US', '🇬🇧': 'GB',
    '🇹🇳': 'TN', '🇹🇷': 'TR', '🇺🇦': 'UA', '🇦🇪': 'AE', '🇳🇱': 'NL', '🇰🇿': 'KZ'
}

EMOJI_NUMBERS = [
    u'\u0030\u20E3',
    u'\u0031\u20E3',
    u'\u0032\u20E3',
    u'\u0033\u20E3',
    u'\u0034\u20E3',
    u'\u0035\u20E3',
    u'\u0036\u20E3',
    u'\u0037\u20E3',
    u'\u0038\u20E3',
    u'\u0039\u20E3',
    u'\U0001F51F'
]

load_dotenv()

with open('translations.json', encoding="utf8") as f:
    translations = json.load(f)


class Map:
    """ A group of attributes representing a map. """

    def __init__(self, name, dev_name, emoji):
        """ Set attributes. """
        self.name = name
        self.dev_name = dev_name
        self.emoji = emoji


def trans(text, *args):
    """"""
    if args:
        try:
            trans_text = translations[Config.lang][text].format(*args)
        except (KeyError, ValueError):
            trans_text = translations['en'][text].format(*args)
    else:
        try:
            trans_text = translations[Config.lang][text].replace('{}', '')
        except (KeyError, ValueError):
            trans_text = translations['en'][text].replace('{}', '')

    return trans_text


def align_text(text, length, align='center'):
    """ Center the text within whitespace of input length. """
    if length < len(text):
        return text

    whitespace = length - len(text)

    if align == 'center':
        pre = math.floor(whitespace / 2)
        post = math.ceil(whitespace / 2)
    elif align == 'left':
        pre = 0
        post = whitespace
    elif align == 'right':
        pre = whitespace
        post = 0
    else:
        raise ValueError('Align argument must be "center", "left" or "right"')

    return ' ' * pre + text + ' ' * post


async def create_emojis(bot):
    """ Upload custom map emojis to guilds. """
    guild = bot.get_guild(Config.main_guild)
    if not guild:
        bot.logger.error(
            'Invalid "EMOJIS_GUILD_ID" value from .env file! closing the bot..')
        await bot.close()

    icons_dic = 'assets/maps/icons/'
    icons = os.listdir(icons_dic)

    guild_emojis_str = [e.name for e in guild.emojis]

    for icon in icons:
        if icon.endswith('.png') and '-' in icon and os.stat(icons_dic + icon).st_size < 256000:
            map_name = icon.split('-')[0]
            map_dev = icon.split('-')[1].split('.')[0]

            if map_dev in guild_emojis_str:
                emoji = discord.utils.get(guild.emojis, name=map_dev)
            else:
                with open(icons_dic + icon, 'rb') as image:
                    try:
                        emoji = await guild.create_custom_emoji(name=map_dev, image=image.read())
                        bot.logger.info(
                            f'Emoji "{emoji.name}" created successfully')
                    except discord.Forbidden:
                        bot.logger.error(
                            'Bot does not have permission to create custom emojis in the specified server')
                        await bot.close()
                    except discord.HTTPException as e:
                        bot.logger.error(
                            f'HTTP exception raised when creating emoji for icon "{map_dev}": {e.text} ({e.code})')
                        await bot.close()
                    except Exception as e:
                        bot.logger.error(f'Exception {e} occurred')
                        await bot.close()

            bot.all_maps[map_dev] = Map(
                map_name,
                map_dev,
                f'<:{map_dev}:{emoji.id}>'
            )
