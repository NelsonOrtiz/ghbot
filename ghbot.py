import discord
from discord.ext import commands
from ext.context import CustomContext
from ext.formatter import EmbedHelp
from collections import defaultdict
from ext import embedtobox
import asyncio
import aiohttp
import datetime
import psutil
import time
import json
import sys
import os
import re
import textwrap
from PIL import Image
import io

class ghbot(commands.Bot):
    '''
    Custom Client for ghbot.py - Made by verix#7200
    '''
    _mentions_transforms = {
        '@everyone': '@\u200beveryone',
        '@here': '@\u200bhere'
    }

    _mention_pattern = re.compile('|'.join(_mentions_transforms.keys()))

    def __init__(gh, **attrs):
        super().__init__(command_prefix=gh.get_pre, gh_bot=True)
        gh.formatter = EmbedHelp()
        gh.session = aiohttp.ClientSession(loop=gh.loop)
        gh.process = psutil.Process()
        gh.prefix = None
        gh._extensions = [x.replace('.py', '') for x in os.listdir('cogs') if x.endswith('.py')]
        gh.last_message = None
        gh.messages_sent = 0
        gh.commands_used = defaultdict(int)
        gh.remove_command('help')
        gh.add_command(gh.ping)
        gh.load_extensions()
        gh.add_command(gh.load)
        gh.add_command(gh.reloadcog)
        gh.load_community_extensions()

    def load_extensions(gh, cogs=None, path='cogs.'):
        '''Loads the default set of extensions or a seperate one if given'''
        for extension in cogs or gh._extensions:
            try:
                gh.load_extension(f'{path}{extension}')
                print(f'Loaded extension: {extension}')
            except Exception as e:
                print(f'LoadError: {extension}\n'
                      f'{type(e).__name__}: {e}')

    def load_community_extensions(gh):
        '''Loads up community extensions.'''
        with open('data/community_cogs.txt') as fp:
            to_load = fp.read().splitlines()
        gh.load_extensions(to_load, 'cogs.community.')

    @property
    def token(gh):
        '''Returns your token wherever it is'''
        with open('data/config.json') as f:
            config = json.load(f)
            if config.get('TOKEN') == "your_token_here":
                if not os.environ.get('TOKEN'):
                    gh.run_wizard()
            else:
                token = config.get('TOKEN').strip('\"')
        return os.environ.get('TOKEN') or token

    @staticmethod
    async def get_pre(bot, message):
        '''Returns the prefix.'''
        with open('data/config.json') as f:
            prefix = json.load(f).get('PREFIX')
        return os.environ.get('PREFIX') or prefix or 'r.'

    def restart(gh):
        os.execv(sys.executable, ['python'] + sys.argv)

    @staticmethod
    def run_wizard():
        '''Wizard for first start'''
        print('------------------------------------------')
        token = input('Enter your token:\n> ')
        print('------------------------------------------')
        prefix = input('Enter a prefix for your ghbot:\n> ')
        data = {
                "TOKEN" : token,
                "PREFIX" : prefix,
            }
        with open('data/config.json','w') as f:
            f.write(json.dumps(data, indent=4))
        print('------------------------------------------')
        print('Restarting...')
        print('------------------------------------------')
        os.execv(sys.executable, ['python'] + sys.argv)

    @classmethod
    def init(bot, token=None):
        '''Starts the actual bot'''
        ghbot = bot()
        safe_token = token or ghbot.token.strip('\"')
        try:
            ghbot.run(safe_token, bot=False, reconnect=True)
        except Exception as e:
            print(e)

    async def on_connect(gh):
        print('---------------\n'
              'ghbot.py connected!')

    async def on_ready(gh):
        '''Bot startup, sets uptime.'''
        if not hasattr(gh, 'uptime'):
            gh.uptime = datetime.datetime.utcnow()
        print(textwrap.dedent(f'''
        Use this at your own risk,
        dont do anything stupid, 
        and when you get banned,
        dont blame it at me.
        ---------------
        Client is ready!
        ---------------
        Author: verixx#7220
        ---------------
        Logged in as: {gh.user}
        User ID: {gh.user.id}
        ---------------
        Current Version: 1.0.0
        ---------------
        '''))
        
        await gh.change_presence(status=discord.Status.invisible, afk=True)

    async def on_command(gh, ctx):
        cmd = ctx.command.qualified_name.replace(' ', '_')
        gh.commands_used[cmd] += 1

    async def process_commands(gh, message):
        '''Utilises the CustomContext subclass of discord.Context'''
        ctx = await gh.get_context(message, cls=CustomContext)
        if ctx.command is None:
            return
        await gh.invoke(ctx)

    async def on_message(gh, message):
        '''Responds only to yourgh'''
        if message.author.id != gh.user.id:
            return
        gh.messages_sent += 1
        gh.last_message = time.time()
        await gh.process_commands(message)
    
    async def on_member_update(gh, before, after):
        if before != gh.user: return
        if before.nick == after.nick: return
        with open('data/options.json') as f:
            options = json.load(f)
        if before.guild.id in options['NICKPROTECT']:
            try:
                await after.edit(nick = None)
            except discord.Forbidden:
                pass

    def get_server(gh, id):
        return discord.utils.get(gh.guilds, id=id)

    @commands.command()
    async def ping(gh, ctx):
        """Pong! Returns your websocket latency."""
        em = discord.Embed()
        em.title ='Pong! Websocket Latency:'
        em.description = f'{gh.ws.latency * 1000:.4f} ms'
        em.color = await ctx.get_dominant_color(ctx.author.avatar_url)
        try:
            await ctx.send(embed=em)
        except discord.HTTPException:
            em_list = await embedtobox.etb(emb)
            for page in em_list:
                await ctx.send(page)

    @commands.command(aliases=["loadcog"])
    async def load(gh, ctx, *, cog: str):
        """ Load an unloaded cog 
        For example: {p}load mod"""
        cog = f"cogs.{cog}"
        await ctx.send(f"Preparing to load {cog}...", delete_after=5)
        try:
            gh.load_extension(cog)
            await ctx.send(f"{cog} cog was loaded successfully!", delete_after=5)
        except Exception as e:
            await ctx.send(f"```py\nError loading {cog}:\n\n{e}\n```", delete_after=5)

    @commands.command(aliases=["reload"])
    async def reloadcog(gh, ctx, *, cog: str):
        """ Reload any cog """
        cog = f"cogs.{cog}"
        await ctx.send(f"Preparing to reload {cog}...", delete_after=5)
        gh.unload_extension(cog)
        try:
            gh.load_extension(cog)
            await ctx.send(f"{cog} cog was reloaded successfully!", delete_after=5)
        except Exception as e:
            await ctx.send(f"```py\nError loading {cog}:\n\n{e}\n```", delete_after=5)


if __name__ == '__main__':
    ghbot.init()
