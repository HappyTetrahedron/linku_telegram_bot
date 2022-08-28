import requests
import datetime


class JasimaCache:
    last_refresh_time: datetime.datetime
    bundle: dict

    MAX_AGE_HOURS = 24
    JSON_LINK = "https://lipu-linku.github.io/jasima/data.json"

    def __init__(self):
        self._refresh()

    @property
    def definitions(self):
        self._refresh_if_needed()
        return self._bundle["data"]

    @property
    def languages(self):
        self._refresh_if_needed()
        return self._bundle["languages"]

    def get_word_entry(self, word):
        entry = self.definitions.get(word)
        if entry:
            return entry
        f = [v for (k, v) in self.definitions.items() if k.lower() == word]
        if len(f) == 1:
            return f[0]
        return None

    def get_by_prefix(self, prefix):
        return {k: v for (k, v) in self.definitions.items() if k.lower().startswith(prefix)}

    def _refresh_if_needed(self):
        if (datetime.datetime.now() - self.last_refresh_time) < datetime.timedelta(hours=self.MAX_AGE_HOURS):
            self._refresh()

    def _refresh(self):
        self._bundle = requests.get(self.JSON_LINK).json()
        self.last_refresh_time = datetime.datetime.now()
