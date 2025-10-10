import os
import regex as re
from collections import defaultdict, deque

import regex as re
from telethon import TelegramClient, events

import metrics

SED_PATTERN = r"^s/((?:\\\S|[^/])+)/((?:\\\S|[^/])*)(/.*)?"
GROUP0_RE = re.compile(r"(?<!\\)((?:\\\\)*)\\0")

bot = TelegramClient(None, 6, "eb06d4abfb49dc3eeb1aeb98ae0f581e")
bot.parse_mode = None

last_msgs: defaultdict[str, deque[str]] = defaultdict(lambda: deque(maxlen=10))


def cleanup_pattern(match):
    from_ = match.group(1)
    to = match.group(2)

    to = to.replace('\\/', '/')
    to = GROUP0_RE.sub(r'\1\\g<0>', to)

    return from_, to


def substitute(fr, to, count, flags, m) -> None | str:
    if not m.raw_text:
        return None

    s, i = re.subn(fr, to, m.raw_text, count=count, flags=flags)
    if i > 0:
        return s

    return None


async def doit(message, match):
    fr, to = cleanup_pattern(match)

    try:
        fl = match.group(3)
        if fl is None:
            fl = ''
        fl = fl[1:]
    except IndexError:
        fl = ''

    # Build Python regex flags
    count = 1
    flags = 0
    for f in fl.lower():
        if f == 'i':
            flags |= re.IGNORECASE
        elif f == 'm':
            flags |= re.MULTILINE
        elif f == 's':
            flags |= re.DOTALL
        elif f == 'g':
            count = 0
        elif f == 'x':
            flags |= re.VERBOSE
        else:
            await message.reply(f"unknown flag: {f}")
            return None

    response = None
    try:
        msg = None
        substitution = None
        if message.is_reply:
            msg = await message.get_reply_message()
            substitution = substitute(fr, to, count, flags, msg)
        else:
            for msg in reversed(last_msgs[message.chat_id]):
                substitution = substitute(fr, to, count, flags, msg)
                if substitution is not None:
                    break  # msg is also set

        if substitution is not None:
            metrics.SUBSTITUTIONS.inc()
            response = await msg.reply(substitution)
    except Exception as e:
        metrics.SED_ERRORS.inc()
        await message.reply("fuck me\n" + str(e))

    return response


@bot.on(events.NewMessage(pattern=r"\/privacy"))
async def privacy(event):
    metrics.MESSAGES_PROCESSED.inc()
    await event.reply(
        "This bot does not collect or process any user data, apart from a short "
        "backlog of messages to perform regex substitutions on. These are not "
        "logged or stored anywhere, and can not be accessed by the bot's "
        "administrator in any way."
    )


@bot.on(events.NewMessage(pattern=SED_PATTERN))
@bot.on(events.MessageEdited(pattern=SED_PATTERN))
async def sed(event):
    metrics.MESSAGES_PROCESSED.inc()
    metrics.SED_COMMANDS.inc()
    with metrics.SUBSTITUTION_LATENCY.time():
        message = await doit(event.message, event.pattern_match)

    if message:
        last_msgs[event.chat_id].append(message)

    # Don't save sed commands or we would be able to sed those
    raise events.StopPropagation


@bot.on(events.NewMessage)
async def catch_all(event):
    metrics.MESSAGES_PROCESSED.inc()
    last_msgs[event.chat_id].append(event.message)
    metrics.UNIQUE_CHATS.set(len(last_msgs))


@bot.on(events.MessageEdited)
async def catch_edit(event):
    metrics.MESSAGES_PROCESSED.inc()
    for i, message in enumerate(last_msgs[event.chat_id]):
        if message.id == event.id:
            last_msgs[event.chat_id][i] = event.message


if __name__ == "__main__":
    metrics.start_http_server(8000)
    with bot.start(bot_token=os.environ["API_KEY"]):
        bot.run_until_disconnected()
