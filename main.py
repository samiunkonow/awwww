from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import uvicorn
from bot import MusicBot

app = FastAPI()

bots = {}  # Diccionario para manejar múltiples bots

class MusicRequest(BaseModel):
    token: str  # Token del bot
    user_id: str
    channel_id: str
    guild_id: str
    query: str

@app.post("/play-music")
async def play_music(request: MusicRequest):
    try:
        if request.token not in bots:
            bot = MusicBot(request.token)
            bots[request.token] = bot
            asyncio.create_task(bot.start_bot())  # Iniciar bot en segundo plano

        bot = bots[request.token]

        result = await bot.play_music(request.user_id, request.channel_id, request.guild_id, request.query)

        return JSONResponse(result, status_code=200)  # ✅ Responder inmediatamente

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
