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

SETTINGS = json.loads(open("cfg.json").read()) # todo add config validation.


def translate(text, from_lang, to_lang):
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


class Mailer(object):
    SERVER = 'smtp.yandex.ru'
    PORT = 465

    def __init__(self, email, passwd):
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

    def mailto(self, content, addressee):
        newsfeed, is_translated = content
        msg = MIMEText(self.template.render(news=newsfeed, translation_used=is_translated), "html")
        msg['Subject'] = "Floydian Newsletter {}".format(self.initdate)
        msg['From'] = "Pink Floyd Mailer <{}>".format(self.my_email)
        msg['To'] = addressee
        self.server_connection.sendmail(self.my_email, addressee, msg.as_string())


def get_latest_news(en_only=True):
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
    mail = input("Email: ")
    passwd = getpass.getpass()
    db.generate_mapping(create_tables=True)
    newsfeed, stamps = get_latest_news()
    if newsfeed:
        with Mailer(mail, passwd) as mailer:
            mailer.mailto(newsfeed, SETTINGS["mail"])
        update_latest_post_urls(stamps)
    else:
        logging.info("There're no updates.")


