import traceback
import datetime
import asyncio
import logging

import discord


BOTE_SPAM = [282500390891683841, 290757101914030080, 207659596167249920]

GUILDS = {
    'HTC':    184755239952318464,
    'HTSTEM': 282219466589208576,
    'Meta':   303365979444871169
}
JOINLOGS = {
    GUILDS['HTC']:    207659596167249920,
    GUILDS['HTSTEM']: 282477076454309888,
    GUILDS['Meta']:   303530104339038209
}
BACKUPS = {
    GUILDS['HTC']:    303374467336241152,
    GUILDS['HTSTEM']: 303374407420608513
}
AVATARLOGS = {
    GUILDS['HTC']: 305337536157450240,
    GUILDS['HTSTEM']: 305337565513515008
}

PREFIX = '!'


class JoinBot:
    def __init__(self, bot):
        super().__init__()

        self.bot = bot

        self.log = logging.getLogger(f'JoinBot')

        self.bannedusers = {}

    @staticmethod
    def clear_formatting(in_string):
        if not in_string.isspace():
            out_string = in_string.replace("`", "​`").replace("*", "​*").replace("_", "​_")  # .replace("", " ")
        else:
            out_string = "[empty string]"

        return out_string

    async def get_user(self, text, guild):
        text = text.strip()

        try:
            text = int(text)
            return guild.get_member(text)
        except ValueError:
            pass

        if text.startswith('<@') and text.endswith('>'):
            text = text[2:-1]
            try:
                args = int(text)
                return guild.get_member(text)
            except ValueError:
                pass

        if guild.large:
            await self.bot.request_offline_members(guild)
        for i in guild.members:
            if i.name == text:
                return i

        return None

    async def broadcast_message(self, msg, guild, avatar=False):
        log_channel = None
        backup_channel = None
        if avatar:
            if guild.id in AVATARLOGS:
                log_channel = self.bot.get_channel(AVATARLOGS[guild.id])

        else:
            if guild.id in JOINLOGS:
                log_channel = self.bot.get_channel(JOINLOGS[guild.id])
            if guild.id in BACKUPS:
                backup_channel = self.bot.get_channel(BACKUPS[guild.id])

        if log_channel is not None:
            try:
                await log_channel.send(msg)
            except Exception:
                self.log.error('An issue occured while trying to send to a joinlog.')
                traceback.print_exc()

        if backup_channel is not None:
            try:
                await backup_channel.send(msg)
            except Exception:
                self.log.error('An issue occured while trying to send to a backup.')
                traceback.print_exc()

    async def on_message(self, message):
        if message.channel.id not in BOTE_SPAM:
            return
        if not message.content.startswith(PREFIX):
            return

        cmd = message.content[len(PREFIX):]
        args = cmd.split(' ', 1)
        cmd = args[0]
        args = ' '.join(args[1:])

        if cmd == 'userinfo':
            if args.strip():
                member = await self.get_user(args, message.guild)
            else:
                member = message.author

            if member is None:
                await message.channel.send('No user found.')
            else:
                username = self.clear_formatting(member.name)
                discrim = f'#{member.discriminator}'

                nickname = 'None'
                if member.nick is not None:
                    nickname = self.clear_formatting(member.nick)

                if member.game is None:
                    game = 'None'
                else:
                    game = self.clear_formatting(member.game.name)

                joined = member.joined_at
                joined_days = datetime.datetime.utcnow() - joined
                joined_days = max(0, joined_days.days)
                created = member.created_at
                created_days = datetime.datetime.utcnow() - created
                created_days = max(0, created_days.days)
                avatar = member.avatar_url

                await message.channel.send(f'''```yaml
╠═► Name:                  {member.name}
╠═► Nickname:              {nickname}
╠═► ID:                    {member.id}
╠═► Discriminator:         {discrim}
╠═► Is A Bot?:             {member.bot}
╠═► Current Game:          {game}
╠═► Roles Here:            {', '.join(i.name for i in member.roles)}
╠═► Avatar:                {avatar}
╠═► Created:               {created} ({created_days} days ago)
╠═► Joined:                {joined} ({joined_days} days ago)
```''')

    async def on_message_delete(self, message):
        pass

    async def on_member_join(self, member):
        if member.guild.id == GUILDS['HTC']:
            await self.bot.change_presence(game=discord.Game(name=f'for {member.guild.member_count} users'))

        time_now = datetime.datetime.utcnow()

        self.log.info(f'A user joined {member.guild.name}: {member} ({member.id})')

        msg = f':white_check_mark: {member.mention} (`{member}` User #{member.guild.member_count}) user joined the server.'
        if not member.avatar_url:
            msg += '\n:no_mouth: User doesn\'t have an avatar.'

        try:
            creation_time = member.created_at
            time_diff = time_now - creation_time

            msg += '\n'
            if time_diff.total_seconds() / 3600 <= 24:
                msg += ':clock1: '

            msg += 'User\'s account was created at ' + creation_time.strftime("%m/%d/%Y %I:%M:%S %p")
        except Exception:
            self.log.error('Something happened while tryin\' to do the timestamp grabby thing:')
            traceback.print_exc()

        await self.broadcast_message(msg, member.guild)

    async def on_member_remove(self, member):
        if member.guild.id == GUILDS['HTC']:
            await self.bot.change_presence(game=discord.Game(name=f'for {member.guild.member_count} users'))

        # Wait for the ban event to fire (if at all)
        await asyncio.sleep(0.25)
        if member.guild.id in self.bannedusers and \
          member.id == self.bannedusers[member.guild.id]:
            del self.bannedusers[member.guild.id]
            return

        self.log.info(f'A user left {member.guild.name}: {member} ({member.id})')

        msg = f':x: {member.mention} (`{member}`) left the server.'
        await self.broadcast_message(msg, member.guild)

    async def on_member_ban(self, guild, member):
        self.bannedusers[guild.id] = member.id
        # Wait for the entry to appear in the audit logs
        await asyncio.sleep(3)

        event = await guild.audit_logs(action=discord.AuditLogAction.ban, limit=1).flatten()
        event = event[0]
        self.log.info(f'A user was banned from {guild.name}: {member} ({member.id})')
        reason = event.reason
        self.log.info(f'Reason: {reason}')

        msg = f':hammer: {member.mention} (`{member}`) was banned from the server. Reason: {reason}'
        await self.broadcast_message(msg, guild)

    async def on_member_unban(self, guild, member):
        self.log.info(f'A user was unbanned from {guild.name}: {member} ({member.id})')

        msg = f':unlock: {member.mention} (`{member}`) was unbanned from the server.'
        await self.broadcast_message(msg, guild)

    async def on_member_update(self, before, after):
        #if before.guild.id == 81384788765712384: return

        if before.name != after.name:
            self.log.info(f'A user ({before.id}) changed their name from {before} to {after}')

            msg = f'User **{before}** changed their name to **{after}** ({after.mention})'
            if before.discriminator != after.discriminator:
                msg += '\n:repeat: *User\'s discriminator changed!*'

            await self.broadcast_message(msg, after.guild)
        elif before.avatar_url != after.avatar_url:
            before_avatar = before.avatar_url_as(format='png')
            after_avatar = after.avatar_url_as(format='png')
            self.log.info(f'{after} ({after.id}) changed their avatar from {before_avatar} to {after_avatar}')

            # This whole thing is hacky. Awaiting d.py update to fix.
            for guild in self.bot.guilds:
                if guild.large:
                    # This is spammy on the console in lage guilds
                    await self.bot.request_offline_members(guild)

                if after in guild.members:
                    msg = f':frame_photo: User **{before}** changed their avatar from {before_avatar} ..'
                    await self.broadcast_message(msg, guild, avatar=True)

                    msg = f'.. to {after_avatar} ({before.mention})'
                    await self.broadcast_message(msg, guild, avatar=True)


def setup(bot):
    bot.add_cog(JoinBot(bot))
