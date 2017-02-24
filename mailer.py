#!/usr/local/bin/python3
import datetime
import getpass
import smtplib
import sys

from email.mime.text import MIMEText
from typing import Tuple, Iterable

import jinja2

from configuration import SETTINGS, SELF_PATH
from database_management import update_latest_post_urls
from parsers import *
from postproc import *


logging.basicConfig(format=u'[%(asctime)s] %(levelname)s. %(message)s', stream=sys.stderr, level=logging.INFO)

PARSERS = [
    AFGParser(),
    BrainDamageParser(),
    FloydianSlipParser(),
    PulseAndSpiritParser(),
]


class SMTPMailer(object):
    """
    A class responsible for sending emails.
    """

    SERVER = SETTINGS["mailer"]["server"]
    PORT = SETTINGS["mailer"]["port"]

    def __init__(self, email: str, passwd: str):
        """
        :param email: An address to use as a sender email.
        :param passwd: A password.
        """
        jloader = jinja2.FileSystemLoader(SELF_PATH)
        self.template = jinja2.Environment(loader=jloader).get_template("message_template.html")
        self.my_email = email
        self._pwd = passwd
        self.initdate = time.strftime("%Y-%m-%d")

    def __enter__(self):
        self.server_connection = smtplib.SMTP_SSL(self.SERVER, self.PORT)
        self.server_connection.login(self.my_email, self._pwd)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.server_connection.quit()

    def mailto(self, newsfeed: List[RawNews], addressee: [str]) -> None:
        """
        Render a newsfeed and send it to adressees from a mailing list.

        :param newsfeed: Newsfeed data - a list of news.
        :param addressee: A list of emails.
        """
        msg = MIMEText(self.template.render(news=newsfeed), "html")
        msg['Subject'] = "Floydian Newsletter {}".format(self.initdate)
        msg['From'] = "Pink Floyd Mailer <{}>".format(self.my_email)
        msg['To'] = ", ".join(addressee)
        self.server_connection.sendmail(self.my_email, addressee, msg.as_string())


ReadyNews = namedtuple("ReadyNews", ["name", "date", "link", "text", "src_lang", "lang"])


def get_latest_news(
        parsers: Iterable[SiteParser],
        filters: Tuple[Predicate, ...] = (),
        en_only: bool=True) -> [ReadyNews]:
    """
    Download the latest news from sources present in a PARSERS list.

    :param parsers: A list of objects parsing necessary sources.
    :param filters: A tuple of filters to apply to the news feed.
    :param en_only: A flag showing whether news not in English should be translated.

    :return: Downloaded newsfeed, timestamp, a flag showing whether a translation's used.
    """
    newsfeed = []
    timestamp = datetime.datetime.now()

    def to_ready_news(news):
        paragraphs, lang = to_paragraphs(news.text), news.parser.lang
        if en_only and lang != "en":
            translation = Converters.translate(paragraphs, lang, "en")
            translated_name = Converters.translate([news.name], lang, "en")
        else:
            translation, translated_name = None, None

        converted_news = ReadyNews(
            name=(translated_name[0] + " / " + news.name) if translated_name else news.name,
            date=news.date,
            link=news.link,
            text=paragraphs if not translation else translation,
            src_lang=lang,
            lang="en" if (translation or translated_name) else lang
        )
        return converted_news

    for parser in parsers:
        news = filter_feed(parser.news, *filters)
        for n in news:
            newsfeed.append(to_ready_news(n))
        update_latest_post_urls(timestamp, news)
    return newsfeed


if __name__ == '__main__':
    filters = (
        SentBefore(),
        IsPreviewOrSonglist(),
    )
    mail = SETTINGS["mailer"]["sender"]
    passwd = getpass.getpass(prompt="Password for {}: ".format(mail))
    newsfeed = get_latest_news(filter(lambda p: p.name in SETTINGS["sources"], PARSERS), filters)
    if newsfeed:
        with SMTPMailer(mail, passwd) as mailer:
            mailer.mailto(newsfeed, SETTINGS["sendto"])
    else:
        logging.info("There're no updates.")


