import discord
from discord.ext import commands
import asyncio
from MusicaBot.buscar import search_youtube
from MusicaBot.audio import get_youtube_audio_url
from youtube_search import YoutubeSearch
import json

bots = {}  # Diccionario global para manejar los bots

class MusicBot(commands.Bot):
    def __init__(self, token):
        super().__init__(command_prefix="!", intents=discord.Intents().all())
        self.token = token
        self.voice_client = None
        self.music_queue = []  # Cola de reproducción
        self.is_playing = False  # Estado de reproducción
        self.ready_event = asyncio.Event()  # Para verificar si el bot está listo

    async def on_ready(self):
        print(f"[{self.token}] Bot conectado y listo.")
        self.ready_event.set()  # Marcar el bot como listo

    async def play_music(self, user_id, channel_id, guild_id, query):
        try:
            await self.ready_event.wait()  # Esperar a que el bot esté listo

            print(f"[{self.token}] Buscando audio para: {query}")
            guild = self.get_guild(int(guild_id))
            if not guild:
                return {"status": 401, "message": f"El bot no está en el servidor {guild_id}."}

            member = guild.get_member(int(user_id))
            if not member or not member.voice or member.voice.channel.id != int(channel_id):
                return {"status": 402, "message": f"El usuario {user_id} no está en el canal de voz correcto."}

            extract = search_youtube(query)
            results = YoutubeSearch(extract, max_results=1).to_json()
            data_url = json.loads(results)

            url = get_youtube_audio_url(extract)
            if not url:
                return {"status": 403, "message": "No se pudo obtener la URL del audio."}

            self.music_queue.append(url)
            print(f"[{self.token}] Agregada a la cola: {url}")

            # Iniciar la reproducción en segundo plano SIN esperar la respuesta
            asyncio.create_task(self.start_playing(int(channel_id)))

            return {"status": 200, "message": "Canción agregada", "queue": self.music_queue, "info_music": data_url}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def start_playing(self, channel_id):
        if self.is_playing or not self.music_queue:
            return

        while self.music_queue:
            url = self.music_queue.pop(0)

            ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
            self.is_playing = True

            if self.voice_client is None or not self.voice_client.is_connected():
                channel = self.get_channel(channel_id)
                if channel is None:
                    print(f"[{self.token}] No se pudo encontrar el canal con ID {channel_id}")
                    return
                
                self.voice_client = await channel.connect()

            self.voice_client.play(discord.FFmpegPCMAudio(url, **ffmpeg_options), after=lambda e: self.check_queue(e))

            while self.voice_client.is_playing():
                await asyncio.sleep(1)

        await self.disconnect_voice()

    def check_queue(self, error=None):
        if error:
            print(f"Error en reproducción: {error}")
        if self.music_queue:
            asyncio.create_task(self.start_playing(self.voice_client.channel.id))
        else:
            self.is_playing = False  # Marcar que ya no está reproduciendo

    async def disconnect_voice(self):
        """Desconecta el bot del canal de voz pero NO lo apaga completamente"""
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
        self.is_playing = False
        print(f"[{self.token}] Bot desconectado del canal de voz, listo para nueva música.")

    async def start_bot(self):
        """Ejecuta el bot en segundo plano sin bloquear"""
        try:
            await self.start(self.token)
        except Exception as e:
            print(f"Error al iniciar el bot: {e}")
