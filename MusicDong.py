import asyncio
import discord
import yt_dlp
import discord.opus
import os
from dotenv import load_dotenv

# .env 파일로부터 환경 변수 로드
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

from discord.ext import commands

# 큐 생성
queue = asyncio.Queue()

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

async def search_youtube(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,  # 출력을 조용하게 유지
        'force_generic_extractor': True,  # 제네릭 추출기 강제 사용
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f'ytsearch:{query}', download=False)['entries'][0]
            return info['url']
        except Exception as e:
            print(f"유튜브에서 검색하는 동안 에러 발생: {e}")
            return None

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
async def play(ctx, *, query):
    # 사용자가 음성 채널에 있는지 확인
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel

        # 봇이 이미 음성 채널에 연결되어 있는지 확인
        if ctx.voice_client:  # 봇이 이미 연결되어 있다면
            vc = ctx.voice_client  # 기존 연결 사용
        else:
            # 봇이 연결되어 있지 않다면 새로 연결
            vc = await channel.connect()

        # 검색된 유튜브 동영상 URL 가져오기
        audio_url = await search_youtube(query)
        if audio_url:
            # 오디오 재생을 위한 FFmpeg 옵션
            ffmpeg_options = {
                'before_options': '-nostdin',
                'options': '-vn -loglevel debug'  # 로그 수준을 debug로 설정
            }

            # 현재 재생 중인 노래가 없으면 바로 재생
            if not vc.is_playing():
                # 오디오 재생
                vc.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options), after=lambda e: print('done', e))

                # YouTube 제목 가져오기
                with yt_dlp.YoutubeDL() as ydl:
                    info = ydl.extract_info(f'ytsearch:{query}', download=False)['entries'][0]
                    title = info.get('title', 'Unknown Title')

                # 재생 중임을 나타내는 메시지 전송
                await ctx.send(f"노래요정이 `{title}`을(를) 재생 중이에요!")

                # 노래가 끝나면 다음 노래를 재생
                while vc.is_playing():
                    await asyncio.sleep(1)
                await play_next(ctx)

            else:
                # 현재 재생 중이던 노래가 있으면 큐에 추가
                await queue.put(audio_url)
                await ctx.send("다음 노래를 예약~!")
        else:
            await ctx.send("검색된 동영상을 찾을 수 없어요!")
    else:
        await ctx.send("음성 채널에 들어가 있지 않아요!")

async def play_next(ctx):
    # 큐에서 다음 노래 URL 가져오기
    if not queue.empty():
        next_url = await queue.get()
        await play(ctx, next_url)
    else:
        # 큐가 비어있으면 음성 채널에서 퇴장
        await ctx.voice_client.disconnect()
        print("음성 채널에서 퇴장")

# @bot.command(aliases=['일시정지'])
# async def pause(ctx):
#     # 봇이 음성 채널에 연결되어 있고 현재 재생 중이라면
#     if ctx.voice_client and ctx.voice_client.is_playing():
#         # 오디오 일시정지
#         ctx.voice_client.pause()
#         await ctx.send("노래요정이 잠깐 쉬고 있어요. 다시 재생하려면 `!다시재생` 명령어를 사용하세요.")
#     else:
#         await ctx.send("현재 재생 중인 음악이 없어요!")

# @bot.command(aliases=['다시재생'])
# async def resume(ctx):
#     # 봇이 음성 채널에 연결되어 있고 현재 일시정지 중이라면
#     if ctx.voice_client and ctx.voice_client.is_paused():
#         # 오디오 다시재생
#         ctx.voice_client.resume()
#         await ctx.send("노래요정이 다시 노래 부르러 왔어요!")
#     else:
#         await ctx.send("현재 일시정지된 음악이 없어요. 먼저 `!일시정지` 명령어로 음악을 일시정지하세요.")


@bot.command(aliases=['정지'])
async def stop(ctx):
    # 봇이 음성 채널에 연결되어 있고 현재 재생 중이라면
    if ctx.voice_client and ctx.voice_client.is_playing():
        # 오디오 재생 중지
        ctx.voice_client.stop()
        await ctx.send("노래요정이 재생을 중지했어요!")
    else:
        await ctx.send("현재 재생 중인 음악이 없어요!")

bot.run(TOKEN)
