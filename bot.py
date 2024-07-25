# -*- coding: utf-8 -*-

import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import os
from dotenv import load_dotenv
from collections import deque

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Cola de canciones
song_queue = deque()

class CustomHelpCommand(commands.HelpCommand):
    def get_ending_note(self):
        return "\n\nType !help <command> for more info on a command.\nType !help <category> for more info on a category.\n ©Xerneas"

    async def send_bot_help(self, mapping):
        destination = self.get_destination()
        help_text = "Available Commands para NINOMEN'S:\n"
        for cog, commands in mapping.items():
            if commands:
                cog_name = cog.qualified_name if cog else "Commands"
                help_text += f"\n**{cog_name}:**\n"
                for command in commands:
                    help_text += f"**{self.get_command_signature(command)}** - {command.help}\n"
        await destination.send(help_text + self.get_ending_note())

    async def send_command_help(self, command):
        destination = self.get_destination()
        help_text = f"**Command:** {self.get_command_signature(command)}\n**Description:** {command.help}"
        await destination.send(help_text)

    async def send_cog_help(self, cog):
        destination = self.get_destination()
        cog_name = cog.qualified_name if cog else "No Category"
        help_text = f"**{cog_name}:**\n"
        for command in cog.get_commands():
            help_text += f"**{self.get_command_signature(command)}** - {command.help}\n"
        await destination.send(help_text + self.get_ending_note())

# Configura el bot para usar el comando de ayuda personalizado
bot.help_command = CustomHelpCommand()

@bot.event
async def on_ready():
    print(f'{bot.user} se ha conectado a Discord!')

@bot.command(name='join', help='Conecta el bot a un canal de voz')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f"Conectado al canal de voz: {channel}")
    else:
        await ctx.send("No estás en un canal de voz!")

@bot.command(name='leave', help='Desconecta el bot del canal de voz')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send("Desconectado del canal de voz")
    else:
        await ctx.send("No estoy en un canal de voz!")

@bot.command(name='play', help='Reproduce un video de YouTube')
async def play(ctx, url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'extractaudio': True,  # solo extraer audio
    }

    if not ctx.author.voice:
        await ctx.send("No estás en un canal de voz!")
        return

    voice_channel = ctx.author.voice.channel
    if not ctx.voice_client:
        await voice_channel.connect()
        await ctx.send(f"Conectado al canal de voz: {voice_channel}")

    voice_client = ctx.voice_client

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            audio_url = next((f['url'] for f in formats if f.get('acodec') != 'none'), None)
            
            if not audio_url:
                # Extraer URL del primer formato de audio si 'acodec' no está disponible
                audio_url = info.get('url')
            
            if audio_url:
                song_queue.append({'url': audio_url, 'title': info['title']})
                await ctx.send(f"Agregado a la cola: {info['title']}")
                
                # Si no está reproduciendo nada, comienza a reproducir
                if not voice_client.is_playing() and not voice_client.is_paused():
                    await play_next_song(ctx)
            else:
                await ctx.send("No se pudo encontrar un formato de audio válido.")
    except Exception as e:
        await ctx.send("Error al reproducir el video")
        print(f"Error al reproducir el video: {e}")

async def play_next_song(ctx):
    if not song_queue:
        await ctx.send("No hay más canciones en la cola.")
        return

    voice_client = ctx.voice_client
    song = song_queue.popleft()
    audio_url = song['url']

    try:
        source = discord.FFmpegPCMAudio(audio_url)
        voice_client.play(source, after=lambda e: bot.loop.create_task(play_next_song(ctx)))
        await ctx.send(f"Reproduciendo: {song['title']}")
    except Exception as e:
        await ctx.send("Error al reproducir la canción")
        print(f"Error al reproducir la canción: {e}")

@bot.command(name='queue', help='Muestra la cola de canciones')
async def queue(ctx):
    if not song_queue:
        await ctx.send("La cola de canciones está vacía.")
    else:
        queue_list = '\n'.join([f"{i+1}. {song['title']}" for i, song in enumerate(song_queue)])
        await ctx.send(f"Cola de canciones:\n{queue_list}")

@bot.command(name='skip', help='Saltar la canción actual')
async def skip(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await play_next_song(ctx)
        await ctx.send("Canción actual saltada.")
    else:
        await ctx.send("No estoy reproduciendo ninguna canción.")

bot.run(TOKEN)
