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
        self.loop_queue = False
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
        results = YoutubeSearch(extract, max_results=1).to_json()
        data_url = json.loads(results)

        if "videos" in data_url and len(data_url["videos"]) > 0:
            video = data_url["videos"][0]
            title = video["title"]
            duration = video["duration"]
            video_url = f"https://www.youtube.com/watch?v={video['id']}"

            self.music_queue.append({"title": title, "url": video_url, "duration": duration})

            if not self.is_playing and not self.is_paused:
                asyncio.create_task(self.start_playing(int(channel_id)))

            return {"status": 200, "message": "Canción agregada", "queue": self.music_queue, "info_music": data_url}

        return {"status": 403, "message": "No se encontraron resultados."}

    async def start_playing(self, channel_id):
        if self.is_playing or not self.music_queue:
            return

        while self.music_queue:
            query = self.music_queue[0]
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
            if self.loop_queue:
                self.music_queue.append(self.music_queue.pop(0))  # Mueve la canción al final
            else:
                self.music_queue.pop(0)  # Elimina la canción si no hay loop

            asyncio.create_task(self.start_playing(self.voice_client.channel.id))
        else:
            self.is_playing = False
    

    async def set_loop_queue(self, enable: bool):
        self.loop_queue = enable
        return {"status": 200, "message": f"Loop del queue {'activado' if enable else 'desactivado'}."}

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

    async def get_queue(self, page: int = 1):
        if not self.music_queue:
            return {"status": 404, "message": "La cola está vacía."}

        items_per_page = 10
        total_pages = (len(self.music_queue) + items_per_page - 1) // items_per_page

        if page < 1 or page > total_pages:
            return {"status": 400, "message": f"Página inválida. Elige entre 1 y {total_pages}."}

        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        queue_list = [
            {"position": i + 1, "title": song["title"], "url": song["url"], "time": song["duration"]}
            for i, song in enumerate(self.music_queue[start_idx:end_idx], start=start_idx)
        ]

        return {
            "status": 200,
            "queue": queue_list,
            "current_page": page,
            "total_pages": total_pages
        }
    
    async def move_queue(self, old_position: int, new_position: int):
        """Mueve una canción de una posición a otra en la cola"""
        if old_position < 1 or old_position > len(self.music_queue):
            return {"status": 400, "message": "Posición inválida en la cola."}

        if new_position < 1 or new_position > len(self.music_queue):
            return {"status": 400, "message": "Nueva posición inválida en la cola."}

        song = self.music_queue.pop(old_position - 1)  # Quitamos la canción de la posición original
        self.music_queue.insert(new_position - 1, song)  # Insertamos en la nueva posición

        return {
            "status": 200,
            "message": f"La canción '{song['title']}' ha sido movida a la posición {new_position}.",
            "queue": self.music_queue
        }

    async def remove_queue(self, position: int):
        """Elimina una canción de la cola según su posición"""
        if position < 1 or position > len(self.music_queue):
            return {"status": 400, "message": "Posición inválida en la cola."}

        removed_song = self.music_queue.pop(position - 1)  # Eliminamos la canción de la cola
        return {
            "status": 200,
            "message": f"La canción '{removed_song['title']}' ha sido eliminada de la cola.",
            "queue": self.music_queue
        }
    
    

    async def start_bot(self):
        try:
            await self.start(self.token)
        except Exception as e:
            print(f"Error al iniciar el bot: {e}")
