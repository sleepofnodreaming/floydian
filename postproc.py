"""
Module containing a set of tools to postprocess a newsfeed.

"""

import abc
import json
import logging
import re
from typing import List, Union

import requests

from configuration import SETTINGS
from database_management import get_latest_post_urls
from parsers import RawNews


class Predicate(metaclass=abc.ABCMeta):
    """
    Base abstract class for predicate creation.
    """

    apply_to = []

    @abc.abstractmethod
    def __call__(self, data: RawNews) -> bool:
        return True


class IsPreviewOrSonglist(Predicate):
    """
    In Floydian Slip, there is a type of posts which is not needed in the feed:
    these are posts about Floydian Slip broadcast.
    This predicate removes them from the feed.
    """

    apply_to = ["Floydian Slip", ]

    def __init__(self):
        self.is_preview = re.compile(
            "^https?://www.floydianslip.com/news/\d+/\d+/floydian-slip-(preview|songlist)-\d+/$",
            flags=re.I | re.U
        )

    def __call__(self, data: RawNews) -> bool:
        """
        Calling the instance with a news post arg checks whether a post
        is a good one or a preview / songlist of a FS broadcast.

        :param data: A RawNews instance.

        :return: A boolean saying whether a text is admitted to the today's news feed.

        >>> from parsers import FloydianSlipParser
        >>> predicate = IsPreviewOrSonglist()
        >>> fsp = FloydianSlipParser()
        >>> songlist_news = RawNews(
        ... fsp, "Any Name", "Date does not matter here",
        ... "http://www.floydianslip.com/news/2016/07/floydian-slip-songlist-1057/",
        ... "Here comes a text", []) # song list post instance
        >>> preview_news = RawNews(
        ... fsp, "Any Name", "Date does not matter here",
        ... "http://www.floydianslip.com/news/2016/07/floydian-slip-preview-1058/",
        ... "Here comes a text", []) # preview post instance
        >>> fs_news = RawNews(
        ... fsp, "Any Name", "Date does not matter here",
        ... "http://www.floydianslip.com/news/2016/07/floydian-slip-coming-to-kcut-102-9-fm-moab-ut/",
        ... "Here comes a text", []) # good FS post instance
        >>> random_news = RawNews(
        ... fsp, "Any Name", "Date does not matter here",
        ... "http://www.brain-damage.co.uk/latest/david-gilmour-in-pompeii-guardian-photo-essay.html",
        ... "Here comes a text", []) # random post instance
        >>> predicate(random_news)
        True
        >>> predicate(fs_news)
        True
        >>> predicate(preview_news)
        False
        >>> predicate(songlist_news)
        False
        """
        if data.parser.name in self.apply_to:
            is_preview = self.is_preview.search(data.link)
            if is_preview:
                logging.warning("Ignored: {} ({} post)".format(data.link, is_preview.group(1)))
                return False
        return True


class SentBefore(Predicate):
    def __init__(self):
        self.sent_before = get_latest_post_urls()

    def __call__(self, data: RawNews) -> bool:
        out = data.link not in self.sent_before
        if not out:
            logging.warning("Ignored: {} ({} post)".format(data.link, "previously published"))
        else:
            logging.info("Approved: {} (not {} post)".format(data.link, "previously published"))
        return out


def filter_feed(newsfeed: [RawNews], *predicates: Predicate) -> [RawNews]:
    """
    Filter the feed with a set of admitting predicates given.

    :param newsfeed: All posts collected.
    :param predicates: Callables getting a News instance as an arg and returning a bool.

    :return: A filtered feed.
    """
    return [post for post in newsfeed if all([i(post) for i in predicates])]


class Converters(object):
    @staticmethod
    def translate(text: [str], from_lang: str, to_lang: str) -> Union[None, List[str]]:
        """
        Translate news texts using Yandex translator API.

        :param text: A list of text pieces to translate.
        :param from_lang: A code of a source language (see  the API reference to get a list of possible values).
        :param to_lang: A code of a language to translate the texts into.

        :return: A list of translated texts, in case of success, and None, otherwise.
        """
        if "translate-key" not in SETTINGS:
            return
        result = requests.get("https://translate.yandex.net/api/v1.5/tr.json/translate", params={
            "key": SETTINGS["translate-key"],
            "text": text,
            "lang": "{}-{}".format(from_lang, to_lang),
            "format": "plain"
        })
        response_json = json.loads(result.text)
        if response_json["code"] != 200:
            logging.warning("Translation failed: {} -> {}.".format(from_lang, to_lang))
            return
        return response_json["text"]