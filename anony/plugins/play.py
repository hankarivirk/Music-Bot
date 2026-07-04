# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pathlib import Path

from pyrogram import filters, types

from anony import anon, app, config, db, lang, queue, tg, yt
from anony.helpers import buttons, utils
from anony.helpers._play import checkUB


PLAYLIST_INLINE_LIMIT = 15


async def playlist_to_queue(chat_id: int, tracks: list) -> tuple[str, str | None]:
    positions = []
    for track in tracks:
        pos = queue.add(chat_id, track)
        positions.append((pos, track))

    if len(positions) > PLAYLIST_INLINE_LIMIT:
        full_list = "\n".join(f"{pos}. {track.title}" for pos, track in positions)
        full_url = await utils.paste(full_list)
        if full_url:
            return "", full_url

    text = "<blockquote expandable>"
    for pos, track in positions:
        text += f"<b>{pos}.</b> {track.title}\n"
    text += "</blockquote>"
    return text, None

@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    m3u8: bool = False,
    video: bool = False,
    url: str = None,
) -> None:
    sent = await m.reply_text(m.lang["play_searching"])
    file = None
    mention = m.from_user.mention
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []

    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    elif m3u8:
        file = await tg.process_m3u8(url, sent.id, video)

    elif url:
        if yt.get_list_id(url):
            await sent.edit_text(m.lang["playlist_fetch"])
            tracks = await yt.playlist(
                config.PLAYLIST_LIMIT, mention, url, video
            )

            if not tracks:
                return await sent.edit_text(m.lang["playlist_error"])

            file = tracks[0]
            tracks.remove(file)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id, video=video)

        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    elif len(m.command) >= 2:
        query = " ".join(m.command[1:])
        file = await yt.search(query, sent.id, video=video)
        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    if not file:
        return await sent.edit_text(m.lang["play_usage"])

    if file.duration_sec > config.DURATION_LIMIT:
        return await sent.edit_text(
            m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60)
        )

    if await db.is_logger():
        await utils.play_log(m, sent.link, file.title, file.duration)

    file.user = mention
    if force:
        queue.force_add(m.chat.id, file)
    else:
        position = queue.add(m.chat.id, file)

        if position != 0 or await db.get_call(m.chat.id):
            await sent.edit_text(
                m.lang["play_queued"].format(
                    position,
                    file.url,
                    file.title,
                    file.duration,
                    m.from_user.mention,
                ),
                reply_markup=buttons.play_queued(
                    m.chat.id, file.id, m.lang["play_now"]
                ),
            )
            if tracks:
                added, full_url = await playlist_to_queue(m.chat.id, tracks)
                notice = m.lang["playlist_full_notice"] if full_url else added
                await app.send_message(
                    chat_id=m.chat.id,
                    text=m.lang["playlist_queued"].format(len(tracks)) + notice,
                    reply_markup=(
                        buttons.ikm([[buttons.ikb(text=m.lang["view_full_list"], url=full_url)]])
                        if full_url else None
                    ),
                )
            return

    if not file.file_path:
        fname = f"downloads/{file.id}.{'mp4' if video else 'webm'}"
        if Path(fname).exists():
            file.file_path = fname
        else:
            await sent.edit_text(m.lang["play_downloading"])
            file.file_path = await yt.download(file.id, video=video)

    await anon.play_media(chat_id=m.chat.id, message=sent, media=file)
    if not tracks:
        return
    added, full_url = await playlist_to_queue(m.chat.id, tracks)
    notice = m.lang["playlist_full_notice"] if full_url else added
    await app.send_message(
        chat_id=m.chat.id,
        text=m.lang["playlist_queued"].format(len(tracks)) + notice,
        reply_markup=(
            buttons.ikm([[buttons.ikb(text=m.lang["view_full_list"], url=full_url)]])
            if full_url else None
        ),
    )
