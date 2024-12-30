import requests
import datetime

DEFAULT_LANGUAGE = "en"
MAX_AGE_HOURS = 24
API_URL = "https://api.linku.la/v1/"
PATH_LANGUAGES = "languages"
PATH_WORDS = "words"
PATH_SANDBOX = "sandbox"
QUERY_LANGUAGE = "lang"

class JasimaCache:
    last_refresh_time: datetime.datetime
    bundle: dict


    def __init__(self):
        self._bundle = {}
        self._last_refresh = {}
        self._refresh(self._language_key(DEFAULT_LANGUAGE))
        self._refresh(self._language_key_sandbox(DEFAULT_LANGUAGE))

    def definitions(self, language=DEFAULT_LANGUAGE):
        self._refresh_if_needed(self._language_key(language))
        return self._bundle[self._language_key(language)]

    def sandbox_definitions(self, language=DEFAULT_LANGUAGE):
        self._refresh_if_needed(self._language_key_sandbox(language))
        return self._bundle[self._language_key_sandbox(language)]

    @property
    def languages(self):
        self._refresh_if_needed(PATH_LANGUAGES)
        return self._bundle[PATH_LANGUAGES]

    def get_word_entry(self, word, language=DEFAULT_LANGUAGE):
        entry = self._find_word_entry(word, self.definitions(language))
        if entry:
            return entry
        entry = self._find_word_entry(word, self.sandbox_definitions(language))
        return entry

    @staticmethod
    def _find_word_entry(word, dictionary):
        entry = dictionary.get(word)
        if entry:
            return entry
        f = [v for (k, v) in dictionary.items() if k.lower() == word]
        if len(f) == 1:
            return f[0]

    def get_by_prefix(self, prefix, language=DEFAULT_LANGUAGE):
        entries = {k: v for (k, v) in self.definitions(language).items() if k.lower().startswith(prefix)}
        if entries:
            return entries
        entries = {k: v for (k, v) in self.sandbox_definitions(language).items() if k.lower().startswith(prefix)}
        return entries

    @staticmethod
    def _language_key(lang):
        return "{}?{}={}".format(PATH_WORDS, QUERY_LANGUAGE, lang)

    @staticmethod
    def _language_key_sandbox(lang):
        return "{}?{}={}".format(PATH_SANDBOX, QUERY_LANGUAGE, lang)

    def _refresh_if_needed(self, path):
        if (datetime.datetime.now() - self._last_refresh.get(path, datetime.datetime.min)) > datetime.timedelta(hours=MAX_AGE_HOURS):
            self._refresh(path)

    def _refresh(self, path):
        print("REFRESHIN {}".format(path))
        self._bundle[path] = requests.get("{}{}".format(API_URL, path)).json()
        self._last_refresh[path] = datetime.datetime.now()
