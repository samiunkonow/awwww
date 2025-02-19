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

class TokenPost(BaseModel):
    token_bot: str


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
async def pause_music(token: TokenPost):
    if token in bots:
        return await bots[token].pause_music()
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/resume-music")
async def resume_music(token: TokenPost):
    if token in bots:
        return await bots[token.token_bot].resume_music()
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/skip-music")
async def skip_music(token: TokenPost):
    if token in bots:
        return await bots[token.token_bot].skip_music()
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/queue")
async def get_queue(token: str):
    if token in bots:
        return await bots[token.token_bot].get_queue()
    return {"status": 404, "message": "Bot no encontrado."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
