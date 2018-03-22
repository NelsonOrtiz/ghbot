
# -*- coding: utf-8 -*-

"""
The MIT License (MIT)
Copyright (c) 2015-2017 Rapptz
Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import itertools
import inspect
import asyncio
import discord
from discord.ext import commands
from discord.ext.commands.core import GroupMixin, Command
from discord.ext.commands.errors import CommandError


class Paginator:
    """A class that aids in paginating embeds for Discord messages.
    Attributes
    -----------
    max_size: int
        The maximum amount of codepoints allowed in a page.
    """
    def __init__(gh, max_size=1200):
        gh.max_size = max_size
        gh._current_embed = discord.Embed()
        gh._current_field = []
        gh._count = 0
        gh._embeds = []
        gh.last_cog = None

    def add_line(gh, line='', *, empty=False):
        """Adds a line to the current embed page.
        If the line exceeds the :attr:`max_size` then an exception
        is raised.
        Parameters
        -----------
        line: str
            The line to add.
        empty: bool
            Indicates if another empty line should be added.
        Raises
        ------
        RuntimeError
            The line was too big for the current :attr:`max_size`.
        """
        if len(line) > gh.max_size - 2:
            raise RuntimeError('Line exceeds maximum page size %s' % (gh.max_size - 2))

        if gh._count + len(line) + 1 > gh.max_size:
            gh.close_page()

        gh._count += len(line) + 1
        gh._current_field.append(line)

        if empty:
            gh._current_field.append('')

    def close_page(gh):
        """Prematurely terminate a page."""
        name = value = ''
        while gh._current_field: 
            curr = gh._current_field.pop(0) # goes through each line
            if curr.strip().endswith(':'): # this means its a CogName:
                if name: 
                    if value:
                        gh._current_embed.add_field(name=name, value=value)
                        name, value = curr, '' # keeps track of the last cog sent,
                        gh.last_cog = curr  # so the next embed can have a `continued` thing                      
                else:                          
                    if value:
                        if gh.last_cog:
                            gh._current_embed.add_field(name=f'{gh.last_cog} (continued)', value=value)
                        value = ''
                    name = curr
                    gh.last_cog = curr
            else:
                value += curr + '\n'

        # adds the last parts not done in the while loop
        print(gh.last_cog)
        if gh.last_cog and value:
            gh._current_embed.add_field(name=gh.last_cog, value=value)
            value = ''

        # this means that there was no `Cog:` title thingys, that means that its a command help
        if value and not gh.last_cog:
            fmt = list(filter(None, value.split('\n')))
            gh._current_embed.title = f'``{fmt[0]}``' # command signiture
            gh._current_embed.description = '\n'.join(fmt[1:]) # command desc

        gh._embeds.append(gh._current_embed)
        gh._current_embed = discord.Embed()
        gh._current_field = []
        gh._count = 1

    @property
    def pages(gh):
        """Returns the rendered list of pages."""
        # we have more than just the prefix in our current page
        if len(gh._current_field) > 1:
            gh.close_page()
        return gh._embeds 

    def __repr__(gh):
        fmt = '<Paginator max_size: {0.max_size} count: {0._count}>'
        return fmt.format(gh)

class EmbedHelp(commands.HelpFormatter):
    """The default base implementation that handles formatting of the help
    command.
    To override the behaviour of the formatter, :meth:`~.HelpFormatter.format`
    should be overridden. A number of utility functions are provided for use
    inside that method.
    Attributes
    -----------
    show_hidden: bool
        Dictates if hidden commands should be shown in the output.
        Defaults to ``False``.
    show_check_failure: bool
        Dictates if commands that have their :attr:`.Command.checks` failed
        shown. Defaults to ``False``.
    width: int
        The maximum number of characters that fit in a line.
        Defaults to 80.
    """
    def __init__(gh, show_hidden=False, show_check_failure=False, width=65):
        gh.width = width
        gh.show_hidden = show_hidden
        gh.show_check_failure = show_check_failure

    def has_subcommands(gh):
        """bool: Specifies if the command has subcommands."""
        return isinstance(gh.command, GroupMixin)

    def is_bot(gh):
        """bool: Specifies if the command being formatted is the bot itgh."""
        return gh.command is gh.context.bot

    def is_cog(gh):
        """bool: Specifies if the command being formatted is actually a cog."""
        return not gh.is_bot() and not isinstance(gh.command, Command)

    def shorten(gh, text):
        """Shortens text to fit into the :attr:`width`."""
        if len(text) > gh.width:
            return text[:gh.width - 3] + '...'
        return text

    @property
    def max_name_size(gh):
        """int: Returns the largest name length of a command or if it has subcommands
        the largest subcommand name."""
        try:
            commands = gh.command.all_commands if not gh.is_cog() else gh.context.bot.all_commands
            if commands:
                return max(map(lambda c: len(c.name) if gh.show_hidden or not c.hidden else 0, commands.values()))
            return 0
        except AttributeError:
            return len(gh.command.name)

    @property
    def clean_prefix(gh):
        """The cleaned up invoke prefix. i.e. mentions are ``@name`` instead of ``<@id>``."""
        user = gh.context.bot.user
        # this breaks if the prefix mention is not the bot itgh but I
        # consider this to be an *incredibly* strange use case. I'd rather go
        # for this common use case rather than waste performance for the
        # odd one.
        return gh.context.prefix.replace(user.mention, '@' + user.name)

    def get_command_signature(gh):
        """Retrieves the signature portion of the help page."""
        prefix = gh.clean_prefix
        cmd = gh.command
        return prefix + cmd.signature

    def get_ending_note(gh):
        command_name = gh.context.invoked_with
        return "Type {0}{1} command for more info on a command.\n" \
               "You can also type {0}{1} category for more info on a category.".format(gh.clean_prefix, command_name)

    async def filter_command_list(gh):
        """Returns a filtered list of commands based on the two attributes
        provided, :attr:`show_check_failure` and :attr:`show_hidden`.
        Also filters based on if :meth:`~.HelpFormatter.is_cog` is valid.
        Returns
        --------
        iterable
            An iterable with the filter being applied. The resulting value is
            a (key, value) tuple of the command name and the command itgh.
        """

        def sane_no_suspension_point_predicate(tup):
            cmd = tup[1]
            if gh.is_cog():
                # filter commands that don't exist to this cog.
                if cmd.instance is not gh.command:
                    return False

            if cmd.hidden and not gh.show_hidden:
                return False

            return True

        async def predicate(tup):
            if sane_no_suspension_point_predicate(tup) is False:
                return False

            cmd = tup[1]
            try:
                return (await cmd.can_run(gh.context))
            except CommandError:
                return False

        iterator = gh.command.all_commands.items() if not gh.is_cog() else gh.context.bot.all_commands.items()
        if gh.show_check_failure:
            return filter(sane_no_suspension_point_predicate, iterator)

        # Gotta run every check and verify it
        ret = []
        for elem in iterator:
            valid = await predicate(elem)
            if valid:
                ret.append(elem)

        return ret

    def _add_subcommands_to_page(gh, max_width, commands):
        for name, command in commands:
            if name in command.aliases:
                # skip aliases
                continue

            entry = '{2.context.prefix}{0:<{width}} {1}'.format(name, command.short_doc, gh, width=max_width)
            shortened = gh.shorten(entry)
            gh._paginator.add_line(f'`{shortened}`')

    async def format_help_for(gh, context, command_or_bot):
        """Formats the help page and handles the actual heavy lifting of how
        the help command looks like. To change the behaviour, override the
        :meth:`~.HelpFormatter.format` method.
        Parameters
        -----------
        context: :class:`.Context`
            The context of the invoked help command.
        command_or_bot: :class:`.Command` or :class:`.Bot`
            The bot or command that we are getting the help of.
        Returns
        --------
        list
            A paginated output of the help command.
        """
        gh.context = context
        gh.command = command_or_bot
        return (await gh.format())

    async def format(gh):
        """Handles the actual behaviour involved with formatting.
        To change the behaviour, this method should be overridden.
        Returns
        --------
        list
            A paginated output of the help command.
        """
        gh._paginator = Paginator()

        # we need a padding of ~80 or so

        description = gh.command.description if not gh.is_cog() else inspect.getdoc(gh.command)

        if description:
            # <description> portion
            gh._paginator.add_line(description, empty=True)

        if isinstance(gh.command, Command):
            # <signature portion>
            signature = gh.get_command_signature()
            gh._paginator.add_line(signature, empty=True)

            # <long doc> section
            if gh.command.help:
                gh._paginator.add_line(gh.command.help, empty=True)

            # end it here if it's just a regular command
            if not gh.has_subcommands():
                gh._paginator.close_page()
                return gh._paginator.pages

        max_width = gh.max_name_size

        def category(tup):
            cog = tup[1].cog_name
            # we insert the zero width space there to give it approximate
            # last place sorting position.
            return cog + ':' if cog is not None else '\u200bNo Category:'

        filtered = await gh.filter_command_list()
        if gh.is_bot():
            data = sorted(filtered, key=category)
            for category, commands in itertools.groupby(data, key=category):
                # there simply is no prettier way of doing this.
                commands = sorted(commands)
                if len(commands) > 0:
                    gh._paginator.add_line(category)

                gh._add_subcommands_to_page(max_width, commands)
        else:
            filtered = sorted(filtered)
            if filtered:
                gh._paginator.add_line('Commands:')
                gh._add_subcommands_to_page(max_width, filtered)

        # add the ending note
        gh._paginator.add_line()
        ending_note = gh.get_ending_note()
        gh._paginator.add_line(ending_note)
        return gh._paginator.pages
