#!/usr/local/bin/python3
import datetime
import getpass
import smtplib
from email.mime.text import MIMEText

import jinja2

from configuration import SETTINGS, SELF_PATH
from database_management import update_latest_post_urls
from parsers import *
from postproc import *
from typing import Tuple

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
        :param email: an address to use as a sender email;
        :param passwd: a password;
        :return: None.

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

    def mailto(self, content: ([News], bool), addressee: [str]) -> None:
        """
        Render a newsfeed and send it to adressees from a mailing list.

        :param content: newsfeed data - a list of news along with a translation success flag;
        :param addressee: a list of emails.
        :return: None.
        
        """
        newsfeed, is_translated = content
        msg = MIMEText(self.template.render(news=newsfeed, translation_used=is_translated), "html")
        msg['Subject'] = "Floydian Newsletter {}".format(self.initdate)
        msg['From'] = "Pink Floyd Mailer <{}>".format(self.my_email)
        msg['To'] = ", ".join(addressee)
        self.server_connection.sendmail(self.my_email, addressee, msg.as_string())


def get_latest_news(filters: Tuple[Predicate] = (), en_only: bool=True) -> ([News], datetime.datetime, bool):
    """
    Download the latest news from sources present in a PARSERS list.

    :param filters: a tuple of filters to apply to the news feed.
    :param en_only: a flag showing whether news not in English should be translated.
    :return: downloaded newsfeed, timestamp, a flag showing whether a translation's used.

    """
    newsfeed = []

    timestamp = datetime.datetime.now()
    translation_used = False

    for parser in PARSERS:
        news = filter_feed(parser.news, *filters)
        if en_only and parser.lang != "en":
            for n in news:
                if n.text:
                    updated_text, translated_successfully = Converters.translate(n.text, parser.lang, "en")
                    if translated_successfully:
                        translation_used = True
                        n.text.clear()
                        n.text.extend(updated_text)
        newsfeed.extend(news)
    return newsfeed, timestamp, translation_used


if __name__ == '__main__':
    filters = (
        SentBefore(),
        IsPreviewOrSonglist(),
    )
    mail = SETTINGS["mailer"]["sender"]
    passwd = getpass.getpass(prompt="Password for {}: ".format(mail))
    newsfeed, timestamp, translation_used = get_latest_news(filters)
    if newsfeed:
        with SMTPMailer(mail, passwd) as mailer:
            mailer.mailto((newsfeed, translation_used), SETTINGS["sendto"])
        update_latest_post_urls(timestamp, newsfeed)
    else:
        logging.info("There're no updates.")


