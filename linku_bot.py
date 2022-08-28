#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import dataset
import yaml
from telegram import InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram.ext.inlinequeryhandler import InlineQueryHandler
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.inline.inlinequeryresultarticle import InlineQueryResultArticle
from telegram.inline.inputtextmessagecontent import InputTextMessageContent

import jasima
import messages

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


class InlineCommands:
    EXPAND = 'EX'
    CONTRACT = 'CT'
    SETLANGUAGE = 'SL'


def _build_etymology(definition):
    etymology = "←"
    if "source_language" in definition:
        etymology += " " + definition["source_language"]
    if "etymology" in definition:
        etymology += " " + definition["etymology"]
    return etymology


class PollBot:
    def __init__(self):
        self.db = None
        self.jasima = jasima.JasimaCache()
        self.debug = False
        self.me = None

    # Command handlers:
    def start(self, update, context):
        """Send a message when the command /start is issued."""
        update.message.reply_text(messages.hello)

    def handle_nimi(self, update, context):
        command = update.message.text
        parts = command.split()
        nimi = parts[1].lower()
        result = self.jasima.get_word_entry(nimi)

        update.message.reply_text(
            text=self._get_definition_for_user(result, update.message.from_user.id),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("show more", callback_data="{}:{}:{}".format(InlineCommands.EXPAND, nimi, update.message.from_user.id))]])
        )

    def handle_language(self, update, context):
        reply_keyboard = []
        settings = self._get_user_settings(update.message.from_user.id)
        for (k, v) in self.jasima.languages.items():
            reply_keyboard.append([
                InlineKeyboardButton(v['name_endonym'], callback_data="{}:{}".format(InlineCommands.SETLANGUAGE, k))
            ])

        update.message.reply_text(
            text=messages.preferences_language.format(language=self.jasima.languages[settings.get('language', 'en')]['name_endonym']),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(reply_keyboard)
        )

    # Inline query handler
    def handle_inline_query(self, update, context):
        query = update.inline_query.query.lower()
        results = self.jasima.get_by_prefix(query)

        inline_results = []

        for word in sorted(results)[:5]:
            inline_results.append(
                InlineQueryResultArticle(
                    id=word,
                    title=word,
                    input_message_content=InputTextMessageContent(
                        parse_mode='Markdown',
                        message_text=self._get_definition_for_user(
                            results[word],
                            update.inline_query.from_user.id
                        ),
                    ),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("show more",
                                                                             callback_data="{}:{}:{}".format(
                                                                                 InlineCommands.EXPAND, word,
                                                                                 update.inline_query.from_user.id))]])
                ),
            )
        update.inline_query.answer(inline_results)

    # Inline button press handler
    def handle_button(self, update, context):
        query = update.callback_query
        data = update.callback_query.data
        parts = data.split(':', 1)

        command = parts[0]
        arg_string = parts[1]

        if query.inline_message_id:
            identifier = {"inline_message_id": query.inline_message_id}
        else:
            identifier = {
                "message_id": query.message.message_id,
                "chat_id": query.message.chat_id,
            }

        match command:
            case InlineCommands.EXPAND:
                arguments = arg_string.split(':', 1)
                context.bot.edit_message_text(
                    **identifier,
                    text=self._get_definition_for_user(self.jasima.get_word_entry(arguments[0]), arguments[1], expand=True),
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                        "show less",
                        callback_data="{}:{}:{}".format(InlineCommands.CONTRACT, arguments[0], arguments[1])
                    )]])
                )
            case InlineCommands.CONTRACT:
                arguments = arg_string.split(':', 1)
                context.bot.edit_message_text(
                    **identifier,
                    text=self._get_definition_for_user(self.jasima.get_word_entry(arguments[0]), arguments[1], expand=False),
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                        "show more",
                        callback_data="{}:{}:{}".format(InlineCommands.EXPAND, arguments[0], arguments[1])
                    )]])
                )
            case InlineCommands.SETLANGUAGE:
                self._set_user_language(parts[1], query.from_user.id)
                settings = self._get_user_settings(query.from_user.id)
                context.bot.edit_message_text(
                    **identifier,
                    text=messages.preferences_language_success.format(language=self.jasima.languages[settings.get('language', 'en')]['name_endonym']),
                    parse_mode="Markdown",
                )
            case _:
                pass

        query.answer("Done!")

# Help command handler
    def handle_help(self, update, context):
        print(self.me)
        update.message.reply_text(messages.help_text.format(botname=self.me['username']), parse_mode="Markdown")

    # Error handler
    def handle_error(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)
        if self.debug:
            import traceback
            traceback.print_exception(context.error)

    # Helper methods
    def _get_definition_for_user(self, definition, user_id, expand=False):
        settings = self._get_user_settings(user_id)
        lang = settings.get('language', 'en')
        if expand:
            body = messages.definition_extended_entry.format(property="description", value=definition['def'][lang])
            if 'etymology' in definition or 'source_language' in definition:
                body += messages.definition_extended_entry.format(property="etymology", value=_build_etymology(definition))
            if 'ku_data' in definition:
                body += messages.definition_extended_entry.format(property="ku data", value=definition['ku_data'])
            if 'commentary' in definition:
                body += messages.definition_extended_entry.format(property="commentary", value=definition['commentary'])
            if definition['book'] not in ('pu', 'ku suli'):
                if 'see_also' in definition:
                    body += messages.definition_extended_entry.format(property="see also", value=definition['see_also'])
            return messages.definition_extended.format(
                word=definition['word'],
                body=body,
            )
        return messages.definition_compact.format(
            word=definition['word'],
            book=definition['book'],
            definition=definition['def'][lang]
        )

    def _set_user_language(self, language, user_id):
        if language not in self.jasima.languages.keys():
            raise ValueError("{} is not a valid language code.".format(language))
        table = self.db['user_settings']
        settings = table.find_one(user_id=user_id)
        if not settings:
            settings = {
                'user_id': user_id
            }
        settings['language'] = language

        if 'id' in settings:
            table.update(settings, keys=["user_id"])
        else:
            table.insert(settings)
        return settings

    def _get_user_settings(self, user_id):
        table = self.db['user_settings']
        settings = table.find_one(user_id=user_id)
        if not settings:
            return {
                'user_id': user_id
            }
        return settings

    def run(self, opts):
        with open(opts.config, 'r') as configfile:
            config = yaml.load(configfile, Loader=yaml.SafeLoader)
        self.debug = config.get('debug', False)

        self.db = dataset.connect('sqlite:///{}'.format(config['db']))

        """Start the bot."""
        # Create the EventHandler and pass it your bot's token.
        updater = Updater(config['token'])

        # Get the dispatcher to register handlers
        dp = updater.dispatcher
        # on different commands - answer in Telegram
        dp.add_handler(CommandHandler("start", self.start))
        dp.add_handler(CommandHandler("help", self.handle_help))
        dp.add_handler(CommandHandler("n", self.handle_nimi))
        dp.add_handler(CommandHandler("nimi", self.handle_nimi))
        dp.add_handler(CommandHandler("language", self.handle_language))
        dp.add_handler(CommandHandler("toki", self.handle_language))

        # Inline queries
        dp.add_handler(InlineQueryHandler(self.handle_inline_query))

        # Callback queries from button presses
        dp.add_handler(CallbackQueryHandler(self.handle_button))

        # log all errors
        dp.add_error_handler(self.handle_error)

        self.me = updater.bot.get_me()

        # Start the Bot
        updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()


def main(opts):
    PollBot().run(opts)


if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-c', '--config', dest='config', default='config.yml', type='string',
                      help="Path of configuration file")
    (opts, args) = parser.parse_args()
    main(opts)
