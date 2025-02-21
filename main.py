from fastapi import FastAPI
import asyncio
from pydantic import BaseModel
from bot import MusicBot

app = FastAPI()
bots = {}

class MusicRequest(BaseModel):
    token: str
    user_id: str
    channel_id: str
    guild_id: str
    query: str

class MoveQueueRequest(BaseModel):
    token: str
    old_position: int
    new_position: int

class RemoveQueueRequest(BaseModel):
    token: str
    position: int


@app.post("/play-music")
async def play_music(request: MusicRequest):
    if request.token not in bots:
        bot = MusicBot(request.token)
        bots[request.token] = bot
        asyncio.create_task(bot.start_bot())

    bot = bots[request.token]
    result = await bot.play_music(request.user_id, request.channel_id, request.guild_id, request.query)
    return result

@app.post("/pause-music")
async def pause_music(token: str):
    if token in bots:
        return await bots[token].pause_music()
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/resume-music")
async def resume_music(token: str):
    if token in bots:
        return await bots[token].resume_music()
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/skip-music")
async def skip_music(token: str):
    if token in bots:
        return await bots[token].skip_music()
    return {"status": 404, "message": "Bot no encontrado."}

@app.get("/queue")
async def get_queue(token: str, page: int = 1):
    if token in bots:
        return await bots[token].get_queue(page)
    return {"status": 404, "message": "Bot no encontrado."}


@app.post("/move-queue")
async def move_queue(request: MoveQueueRequest):
    if request.token in bots:
        return await bots[request.token].move_queue(request.old_position, request.new_position)
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/remove-queue")
async def remove_queue(request: RemoveQueueRequest):
    if request.token in bots:
        return await bots[request.token].remove_queue(request.position)
    return {"status": 404, "message": "Bot no encontrado."}


@app.get("/loop-queue")
async def loop_queue(token: str, enable: bool):
    if token in bots:
        return await bots[token].set_loop_queue(enable)
    return {"status": 404, "message": "Bot no encontrado."}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
