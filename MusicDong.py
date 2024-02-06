import discord
import yt_dlp
import discord.opus
import os
from dotenv import load_dotenv

# .env 파일로부터 환경 변수 로드
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

from discord.ext import commands

# Opus 로딩 상세 출력
print("Loading Opus...")
try:
    discord.opus.load_opus('/Users/donggyunkim/miniforge3/lib/libopus.dylib')  # 여러분의 Opus 라이브러리 경로로 변경
    if not discord.opus.is_loaded():
        raise RuntimeError('Opus failed to load')
    print('Opus loaded successfully!')
except Exception as e:
    print(f'Opus failed to load: {e}')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print('{0.user} 봇을 실행합니다.'.format(bot))

@bot.command(aliases=['입장'])
async def join(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel
        await ctx.send("노래요정 {0.author.voice.channel} 채널에 등장!~".format(ctx))
        await channel.connect()
        print("음성 채널 정보: {0.author.voice}".format(ctx))
        print("음성 채널 이름: {0.author.voice.channel}".format(ctx))
    else:
        await ctx.send("아무도 음성 채널에 존재하지 않아!")

@bot.command(aliases=['퇴장'])
async def out(ctx):
    try:
        await ctx.voice_client.disconnect()
        await ctx.send("노래요정 {0.author.voice.channel} 채널에서 퇴장~".format(ctx))
    except IndexError as error_message:
        print(f"에러 발생: {error_message}")
        await ctx.send("{0.author.voice.channel}에 유저가 존재하지 않거나 봇이 존재하지 않습니다.\\n다시 입장후 퇴장시켜주세요.".format(ctx))
    except AttributeError as not_found_channel:
        print(f"에러 발생: {not_found_channel}")
        await ctx.send("노래요정은 그 어디에도 존재하지 않는다,,, ㄷㄷㄷㄷ")


async def extract_audio_url(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_info = None
        for f in info['formats']:
            # 'acodec' 키가 존재하고 오디오 코덱이 'none'이 아닌지 확인
            if f.get('acodec') and f['acodec'] != 'none':
                audio_info = f
                break

        if audio_info:
            return audio_info['url']  # 오디오 스트림 URL을 반환합니다.
        else:
            return None

@bot.command(aliases=['재생'])
async def play(ctx, url):
    # 사용자가 음성 채널에 있는지 확인
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel

        # 봇이 이미 음성 채널에 연결되어 있는지 확인
        if ctx.voice_client:  # 봇이 이미 연결되어 있다면
            vc = ctx.voice_client  # 기존 연결 사용
        else:
            # 봇이 연결되어 있지 않다면 새로 연결
            vc = await channel.connect()

        # 오디오 URL 추출
        audio_url = await extract_audio_url(url)
        if audio_url:
            # 오디오 재생을 위한 FFmpeg 옵션
            ffmpeg_options = {
                'before_options': '-nostdin',
                'options': '-vn -loglevel debug'  # 로그 수준을 debug로 설정
            }

            # 오디오 재생
            vc.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options), after=lambda e: print('done', e))

            # 재생 중임을 나타내는 메시지 전송
            await ctx.send(f"노래요정이 `{url}`을(를) 재생 중이에요!")
        else:
            await ctx.send("오디오 URL을 찾을 수 없어요!")
    else:
        await ctx.send("음성 채널에 들어가 있지 않아요!")



bot.run(TOKEN)
