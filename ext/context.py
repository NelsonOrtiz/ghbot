import discord
from discord.ext import commands
import asyncio
from colorthief import ColorThief
from urllib.parse import urlparse
import io
import os
import base64

class CustomContext(commands.Context):
    '''Clase de contexto personalizado para proporcionar utilidad.'''
    def __init__(gh, **kwargs):
        super().__init__(**kwargs)

    @property
    def session(gh):
        '''Devuelve la sesión del cliente aiohttp del bot'''
        return gh.bot.session

    def delete(gh):
        '''atajo'''
        return gh.message.delete()

    async def get_ban(gh, name_or_id):
        '''Función de ayuda para recuperar un usuario prohibido'''
        for ban in await gh.guild.bans():
            if name_or_id.isdigit():
                if ban.user.id == int(name_or_id):
                    return ban
            if name_or_id.lower() in str(ban.user).lower():
                return ban

    async def purge(gh, *args, **kwargs):
        '''Acceso directo a channel.purge, preestablecido para ghbots.'''
        kwargs.setdefault('bulk', False)
        await gh.channel.purge(*args, **kwargs)

    async def _get_message(gh, channel, id):
        '''Recorre el historial del canal para obtener un mensaje'''
        async for message in channel.history(limit=2000):
            if message.id == id:
                return message

    async def get_message(gh, channel_or_id, id=None):
        '''Herramienta de ayuda para recibir un mensaje de ghbots'''
        if isinstance(channel_or_id, int):
            msg = await gh._get_message(channel=gh.channel, id=channel_or_id)
        else:
            msg = await gh._get_message(channel=channel_or_id, id=id)
        return msg

    async def confirm(gh, msg):
        '''Pequeño ayudante para mensajes de confirmación.'''
        await gh.send(msg or '*Estas seguro que deseas continuar?* `(S/N)`')
        resp = gh.bot.wait_for('message', check=lambda m: m == ctx.author)
        falsy = ['n', 'no', 'false','0','fuck off','f']
        if resp.content.lower().strip() in falsy:
            return False
        else:
            return True

    async def send_cmd_help(gh):
        '''Enviar comando de ayuda'''
        if gh.invoked_subcommand:
            pages = gh.formatter.format_help_for(gh, gh.invoked_subcommand)
            for page in pages:
                await gh.send_message(gh.message.channel, page)
        else:
            pages = gh.formatter.format_help_for(gh, gh.command)
            for page in pages:
                await gh.send_message(gh.message.channel, page)

    @staticmethod
    def is_valid_image_url(url):
        '''Comprueba si una URL conduce a una imagen.'''
        types = ['.png', '.jpg', '.gif', '.bmp', '.webp']
        parsed = urlparse(url)
        if any(parsed.path.endswith(i) for i in types):
            return url.replace(parsed.query, 'size=128')

    async def get_dominant_color(gh, url=None, quality=10):
        '''Devuelve el color dominante de una imagen desde una url'''
        maybe_col = os.environ.get('COLOR')

        url = url or gh.author.avatar_url

        if maybe_col:
            raw = int(maybe_col.strip('#'), 16)
            return discord.Color(value=raw)

        if not gh.is_valid_image_url(url):
            raise ValueError('La URL de la imagen no es válida.')
        try:
            async with gh.session.get(url) as resp:
                image = await resp.read()
        except:
            return discord.Color.default()

        with io.BytesIO(image) as f:
            try:
                color = ColorThief(f).get_color(quality=quality)
            except:
                return discord.Color.dark_grey()
            
        return discord.Color.from_rgb(*color)

    async def success(gh, msg=None, delete=False):
        if delete:
            await gh.message.delete()
        if msg:
            await gh.send(msg)
        else:
            await gh.message.add_reaction('✅')

    async def failure(gh, msg=None):
        if msg:
            await gh.send(msg)
        else:
            await gh.message.add_reaction('⁉')

    
    async def updatedata(gh, path:str, content:str, commitmsg='Sin mensaje de compromiso'):
        '''Para editar datos en Github'''
        git = gh.bot.get_cog('Git')
        #get username
        username = await git.githubusername()
        #get sha (dont even know why this is a compulsory field)
        async with gh.session.get(f'https://api.github.com/repos/{username}/ghbot.py/contents/{path}', headers={"Authorization": f"Bearer {git.githubtoken}"}) as resp2:
            if 300 > resp2.status >= 200:
                #push to path
                async with gh.session.put(f'https://api.github.com/repos/{username}/ghbot.py/contents/{path}', headers={"Authorization": f"Bearer {git.githubtoken}"}, json={"path":"data/cc.json", "message":commitmsg, "content":base64.b64encode(bytes(content, 'utf-8')).decode('ascii'), "sha":(await resp2.json())['sha'], "branch":"rewrite"}) as resp3:
                    if 300 > resp3.status >= 200:
                        return True
                        #data pushed successfully
                    else:
                        await gh.send('Well, I failed somehow, send the following to `4JR#2713` (180314310298304512): ```py\n' + str(await resp3.json()) + '\n```')
                        return False 
            else:
                await gh.send('Well, I failed somehow, send the following to `4JR#2713` (180314310298304512): ```py\n' + str(await resp2.json()) + '\n```')
                return False

    @staticmethod
    def paginate(text: str):
        '''Simple generator that paginates text.'''
        last = 0
        pages = []
        for curr in range(0, len(text)):
            if curr % 1980 == 0:
                pages.append(text[last:curr])
                last = curr
                appd_index = curr
        if appd_index != len(text)-1:
            pages.append(text[last:curr])
        return list(filter(lambda a: a != '', pages))
