#!/usr/local/bin/python3
import datetime
import getpass
import jinja2
import json
import os
import requests
import smtplib
from database_management import *
from parsers import *
from email.mime.text import MIMEText

PARSERS = [
    AFGParser(),
    BrainDamageParser(),
    FloydianSlipParser(),
    PulseAndSpiritParser(),
]

SELF_PATH = os.path.dirname(os.path.realpath(__file__))

SETTINGS = json.loads(open(os.path.join(SELF_PATH, "cfg.json")).read()) # todo add config validation.


def translate(text: [str], from_lang: str, to_lang: str) -> ([str], bool):
    """
    Translate news texts using Yandex translator API.

    :param text: a list of text pieces to translate;
    :param from_lang: a code of a source language (see  the API reference to get a list of possible values);
    :param to_lang: a code of a language to translate the texts into.
    :return: a list of translated texts, in case of success, and the initial one, otherwise;
    a flag showing whether the texts were translated.

    """
    result = requests.get("https://translate.yandex.net/api/v1.5/tr.json/translate", params={
        "key": SETTINGS["translate-key"],
        "text": text,
        "lang": "{}-{}".format(from_lang, to_lang),
        "format": "plain"
    })
    response_json = json.loads(result.text)
    if response_json["code"] == 200:
        return response_json["text"], True
    else:
        logging.warning("Translation failed: {} -> {}.".format(from_lang, to_lang))
        return text, False


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
        jloader = jinja2.FileSystemLoader(os.path.dirname(os.path.realpath(__file__)))
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


def get_latest_news(en_only: bool=True) -> (([News], bool), [NewsStamp]):
    """
    Download the latest news from sources present in a PARSERS list.

    :param en_only: a flag showing whether news not in English should be translated.
    :return: downloaded newsfeed and a list of the last post published for each source.

    """
    breakpoints = get_latest_post_urls()

    newsfeed, stamps = [], []

    ts = datetime.now()
    translation_used = False

    for parser in PARSERS:
        news = parser.news
        if parser.name in breakpoints:
            try:
                url_list = [n.link for n in news]
                news = news[:url_list.index(breakpoints[parser.name])]
            except ValueError:
                logging.error("Incorrect latest post in the database: parser {}".format(parser.name))
        if en_only and parser.lang != "en":
            for n in news:
                if n.text:
                    updated_text, translated_successfully = translate(n.text, parser.lang, "en")
                    if translated_successfully:
                        translation_used = True
                        n.text.clear()
                        n.text.extend(updated_text)
        newsfeed.extend(news)
        if news:
            stamps.append(NewsStamp(parser.name, parser.mainpage, news[0].link, ts))

    return (newsfeed, translation_used), stamps


if __name__ == '__main__':
    mail = SETTINGS["mailer"]["sender"]
    passwd = getpass.getpass(prompt="Password for {}: ".format(mail))
    db.generate_mapping(create_tables=True)
    newsfeed, stamps = get_latest_news()
    if newsfeed:
        with SMTPMailer(mail, passwd) as mailer:
            mailer.mailto(newsfeed, SETTINGS["sendto"])
        update_latest_post_urls(stamps)
    else:
        logging.info("There're no updates.")


