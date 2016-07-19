#!/usr/local/bin/python3
import datetime
import getpass
import jinja2
import smtplib

from configuration import SETTINGS, SELF_PATH
from database_management import *
from email.mime.text import MIMEText
from parsers import *
from postproc import Converters, filter_feed, IsPreviewOrSonglist

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
        news = filter_feed(parser.news, IsPreviewOrSonglist())
        if parser.name in breakpoints:
            try:
                url_list = [n.link for n in news]
                news = news[:url_list.index(breakpoints[parser.name])]
            except ValueError:
                logging.error("Incorrect latest post in the database: parser {}".format(parser.name))
        if en_only and parser.lang != "en":
            for n in news:
                if n.text:
                    updated_text, translated_successfully = Converters.translate(n.text, parser.lang, "en")
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


