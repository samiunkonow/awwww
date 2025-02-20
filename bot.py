import discord
from discord.ext import commands
import asyncio
from MusicaBot.buscar import search_youtube
from MusicaBot.audio import get_youtube_audio_url
from youtube_search import YoutubeSearch
import json

bots = {}

class MusicBot(commands.Bot):
    def __init__(self, token):
        super().__init__(command_prefix="!", intents=discord.Intents().all())
        self.token = token
        self.voice_client = None
        self.music_queue = []
        self.is_playing = False
        self.is_paused = False
        self.ready_event = asyncio.Event()

    async def on_ready(self):
        print(f"[{self.token}] Bot conectado y listo.")
        self.ready_event.set()

    async def play_music(self, user_id, channel_id, guild_id, query):
        await self.ready_event.wait()

        guild = self.get_guild(int(guild_id))
        if not guild:
            return {"status": 401, "message": f"El bot no está en el servidor {guild_id}."}

        member = guild.get_member(int(user_id))
        if not member or not member.voice or member.voice.channel.id != int(channel_id):
            return {"status": 402, "message": f"El usuario {user_id} no está en el canal de voz correcto."}

        extract = search_youtube(query)
        print("extract: ", extract)
        results = YoutubeSearch(extract, max_results=1).to_json()
        print("results: ", results)
        data_url = json.loads(results)

        if "videos" in data_url and len(data_url["videos"]) > 0:
            video = data_url["videos"][0]
            title = video["title"]
            video_url = f"https://www.youtube.com/watch?v={video['id']}"

            self.music_queue.append({"title": title, "url": video_url})

            if not self.is_playing and not self.is_paused:
                asyncio.create_task(self.start_playing(int(channel_id)))

            return {"status": 200, "message": "Canción agregada", "queue": self.music_queue, "info_music": data_url}

        return {"status": 403, "message": "No se encontraron resultados."}

    async def start_playing(self, channel_id):
        if self.is_playing or not self.music_queue:
            return

        while self.music_queue:
            query = self.music_queue.pop(0)
            url = get_youtube_audio_url(query["url"])
            ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

            self.is_playing = True
            self.is_paused = False

            if self.voice_client is None or not self.voice_client.is_connected():
                channel = self.get_channel(channel_id)
                if channel is None:
                    print(f"[{self.token}] No se pudo encontrar el canal con ID {channel_id}")
                    return
                
                self.voice_client = await channel.connect()

            self.voice_client.play(discord.FFmpegPCMAudio(url, **ffmpeg_options), after=lambda e: self.check_queue())

            while self.voice_client.is_playing() or self.is_paused:
                await asyncio.sleep(1)

        if not self.is_paused:
            await self.disconnect_voice()

    def check_queue(self):
        if self.music_queue:
            asyncio.create_task(self.start_playing(self.voice_client.channel.id))
        else:
            self.is_playing = False

    async def disconnect_voice(self):
        if self.voice_client and not self.is_paused:
            await self.voice_client.disconnect()
            self.voice_client = None
            self.is_playing = False
            print(f"[{self.token}] Bot desconectado del canal de voz.")

    async def pause_music(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.is_paused = True
            self.is_playing = False  # Se detiene la reproducción pero no se desconecta
            return {"status": 200, "message": "Música pausada."}
        return {"status": 404, "message": "No hay música reproduciéndose."}

    async def resume_music(self):
        if self.voice_client and self.is_paused:
            self.voice_client.resume()
            self.is_paused = False
            self.is_playing = True
            return {"status": 200, "message": "Música reanudada."}
        return {"status": 404, "message": "No hay música pausada."}

    async def skip_music(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
            return {"status": 200, "message": "Saltando a la siguiente canción."}
        return {"status": 404, "message": "No hay música reproduciéndose."}

    async def get_queue(self):
        if not self.music_queue:
            return {"status": 404, "message": "La cola está vacía."}

        queue_list = [f"[{song['title']}]({song['url']})" for song in self.music_queue]
        return {"status": 200, "queue": queue_list}

    async def start_bot(self):
        try:
            await self.start(self.token)
        except Exception as e:
            print(f"Error al iniciar el bot: {e}")
