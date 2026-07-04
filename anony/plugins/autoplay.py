# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import filters, types

from anony import app, db, lang
from anony.helpers import can_manage_vc


@app.on_message(filters.command(["autoplay"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _autoplay(_, m: types.Message):
    chat_id = m.chat.id

    if len(m.command) < 2:
        status = m.lang["autoplay_on"] if await db.get_autoplay(chat_id) else m.lang["autoplay_off"]
        return await m.reply_text(m.lang["autoplay_status"].format(status))

    arg = m.command[1].lower()
    if arg in ["on", "enable"]:
        await db.set_autoplay(chat_id, True)
        return await m.reply_text(m.lang["autoplay_enabled"])
    elif arg in ["off", "disable"]:
        await db.set_autoplay(chat_id, False)
        return await m.reply_text(m.lang["autoplay_disabled"])

    await m.reply_text(m.lang["autoplay_usage"])
