import logging
import yt_dlp
from asyncio import sleep
from threading import Thread
from os import makedirs, path as ospath
from colab_leecher.utility.handler import cancelTask
from colab_leecher.utility.variables import YTDL, MSG, Messages, Paths, Transfer, BOT, BotTimes
from colab_leecher.utility.helper import getTime, keyboard, sizeUnit, status_bar, sysINFO, fileType, thumbMaintainer, videoExtFix

async def YTDL_Status(link, num):
    global Messages, YTDL
    name = await get_YT_Name(link)
    Messages.status_head = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<code>{name}</code>\n"

    YTDL_Thread = Thread(target=YouTubeDL, name="YouTubeDL", args=(link,))
    YTDL_Thread.start()

    while YTDL_Thread.is_alive():  # Until ytdl is downloading
        if YTDL.header:
            sys_text = sysINFO()
            message = YTDL.header
            try:
                await MSG.status_msg.edit_text(text=Messages.task_msg + Messages.status_head + message + sys_text, reply_markup=keyboard())
            except Exception:
                pass
        else:
            try:
                await status_bar(
                    down_msg=Messages.status_head,
                    speed=YTDL.speed,
                    percentage=float(YTDL.percentage),
                    eta=YTDL.eta,
                    done=YTDL.done,
                    left=YTDL.left,
                    engine="Xr-YtDL 🏮",
                )
            except Exception:
                pass

        await sleep(2.5)

    # After download completes, upload the file
    downloaded_file_path = YTDL.final_file_path
    real_name = YTDL.real_name
    await upload_file(downloaded_file_path, real_name)

class MyLogger:
    def __init__(self):
        pass

    def debug(self, msg):
        global YTDL
        if "item" in str(msg):
            msgs = msg.split(" ")
            YTDL.header = f"\n⏳ __Getting Video Information {msgs[-3]} of {msgs[-1]}__"

    @staticmethod
    def warning(msg):
        pass

    @staticmethod
    def error(msg):
        pass

def YouTubeDL(url):
    global YTDL

    def my_hook(d):
        global YTDL

        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes", 0)  # Use 0 as default if total_bytes is None
            dl_bytes = d.get("downloaded_bytes", 0)
            percent = d.get("downloaded_percent", 0)
            speed = d.get("speed", "N/A")
            eta = d.get("eta", 0)

            if total_bytes:
                percent = round((float(dl_bytes) * 100 / float(total_bytes)), 2)

            YTDL.header = ""
            YTDL.speed = sizeUnit(speed) if speed else "N/A"
            YTDL.percentage = percent
            YTDL.eta = getTime(eta) if eta else "N/A"
            YTDL.done = sizeUnit(dl_bytes) if dl_bytes else "N/A"
            YTDL.left = sizeUnit(total_bytes) if total_bytes else "N/A"

        elif d["status"] == "downloading fragment":
            pass
        elif d["status"] == "finished":
            YTDL.final_file_path = d["filename"]
            YTDL.real_name = ospath.basename(d["filename"])
        else:
            logging.info(d)

    ydl_opts = {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "allow_multiple_video_streams": True,
        "allow_multiple_audio_streams": True,
        "writethumbnail": True,
        "--concurrent-fragments": 4,
        "allow_playlist_files": True,
        "overwrites": True,
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        "progress_hooks": [my_hook],
        "writesubtitles": "srt",
        "extractor_args": {"subtitlesformat": "srt"},
        "logger": MyLogger(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if not ospath.exists(Paths.thumbnail_ytdl):
            makedirs(Paths.thumbnail_ytdl)
        try:
            info_dict = ydl.extract_info(url, download=False)
            YTDL.header = "⌛ __Please WAIT a bit...__"
            if "_type" in info_dict and info_dict["_type"] == "playlist":
                playlist_name = info_dict["title"]
                if not ospath.exists(ospath.join(Paths.down_path, playlist_name)):
                    makedirs(ospath.join(Paths.down_path, playlist_name))
                ydl_opts["outtmpl"] = {
                    "default": f"{Paths.down_path}/{playlist_name}/%(title)s.%(ext)s",
                    "thumbnail": f"{Paths.thumbnail_ytdl}/%(title)s.%(ext)s",
                }
                for entry in info_dict["entries"]:
                    video_url = entry["webpage_url"]
                    try:
                        ydl.download([video_url])
                    except yt_dlp.utils.DownloadError as e:
                        if e.exc_info[0] == 36:
                            ydl_opts["outtmpl"] = {
                                "default": f"{Paths.down_path}/%(title)s.%(ext)s",
                                "thumbnail": f"{Paths.thumbnail_ytdl}/%(title)s.%(ext)s",
                            }
                            ydl.download([video_url])
            else:
                YTDL.header = ""
                ydl_opts["outtmpl"] = {
                    "default": f"{Paths.down_path}/%(title)s.%(ext)s",
                    "thumbnail": f"{Paths.thumbnail_ytdl}/%(title)s.%(ext)s",
                }
                try:
                    ydl.download([url])
                except yt_dlp.utils.DownloadError as e:
                    if e.exc_info[0] == 36:
                        ydl_opts["outtmpl"] = {
                            "default": f"{Paths.down_path}/%(title)s.%(ext)s",
                            "thumbnail": f"{Paths.thumbnail_ytdl}/%(title)s.%(ext)s",
                        }
                        ydl.download([url])
        except Exception as e:
            logging.error(f"YTDL ERROR: {e}")

async def get_YT_Name(link):
    with yt_dlp.YoutubeDL({"logger": MyLogger()}) as ydl:
        try:
            info = ydl.extract_info(link, download=False)
            if "title" in info and info["title"]:
                return info["title"]
            else:
                return "UNKNOWN DOWNLOAD NAME"
        except Exception as e:
            await cancelTask(f"Can't Download from this link. Because: {str(e)}")
            return "UNKNOWN DOWNLOAD NAME"

async def progress_bar(current, total):
    global status_msg, status_head
    upload_speed = 4 * 1024 * 1024
    elapsed_time_seconds = (datetime.now() - BotTimes.task_start).seconds
    if current > 0 and elapsed_time_seconds > 0:
        upload_speed = current / elapsed_time_seconds
    eta = (Transfer.total_down_size - current - sum(Transfer.up_bytes)) / upload_speed
    percentage = (current + sum(Transfer.up_bytes)) / Transfer.total_down_size * 100

    if current % (total // 100) == 0:  # Update every 1% progress
        await status_bar(
            down_msg=Messages.status_head,
            speed=f"{sizeUnit(upload_speed)}/s",
            percentage=percentage,
            eta=getTime(eta),
            done=sizeUnit(current + sum(Transfer.up_bytes)),
            left=sizeUnit(Transfer.total_down_size),
            engine="Pyrogram 💥",
        )

async def upload_file(file_path, real_name):
    global Transfer, MSG
    BotTimes.task_start = datetime.now()
    caption = f"<{BOT.Options.caption}>{BOT.Setting.prefix} {real_name} {BOT.Setting.suffix}</{BOT.Options.caption}>"
    type_ = fileType(file_path)

    f_type = type_ if BOT.Options.stream_upload else "document"

    # Upload the file
    try:
        if f_type == "video":
            # For Renaming to mp4
            if not BOT.Options.stream_upload:
                file_path = videoExtFix(file_path)
            # Generate Thumbnail and Get Duration
            thmb_path, seconds = thumbMaintainer(file_path)
            with Image.open(thmb_path) as img:
                width, height = img.size

            MSG.sent_msg = await MSG.sent_msg.reply_video(
                video=file_path,
                supports_streaming=True,
                width=width,
                height=height,
                caption=caption,
                thumb=thmb_path,
                duration=int(seconds),
                progress=progress_bar,
                reply_to_message_id=MSG.sent_msg.id,
            )

        elif f_type == "audio":
            thmb_path = None if not ospath.exists(Paths.THMB_PATH) else Paths.THMB_PATH
            MSG.sent_msg = await MSG.sent_msg.reply_audio(
                audio=file_path,
                caption=caption,
                thumb=thmb_path,  # type: ignore
                progress=progress_bar,
                reply_to_message_id=MSG.sent_msg.id,
            )

        elif f_type == "document":
            if ospath.exists(Paths.THMB_PATH):
                thmb_path = Paths.THMB_PATH
            elif type_ == "video":
                thmb_path, _ = thumbMaintainer(file_path)
            else:
                thmb_path = None

            MSG.sent_msg = await MSG.sent_msg.reply_document(
                document=file_path,
                caption=caption,
                thumb=thmb_path,  # type: ignore
                progress=progress_bar,
                reply_to_message_id=MSG.sent_msg.id,
            )

        elif f_type == "photo":
            MSG.sent_msg = await MSG.sent_msg.reply_photo(
                photo=file_path,
                caption=caption,
                progress=progress_bar,
                reply_to_message_id=MSG.sent_msg.id,
            )

        Transfer.sent_file.append(MSG.sent_msg)
        Transfer.sent_file_names.append(real_name)

    except FloodWait as e:
        logging.warning(f"FloodWait: {e.x} seconds")
        await sleep(e.x)
        await upload_file(file_path, real_name)
    except Exception as e:
        logging.error(f"Error When Uploading : {e}")
