import jinja2
import os
import smtplib
import time
from email.mime.text import MIMEText


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
        msg = MIMEText(self.template.render(news=content), "html")
        msg['Subject'] = "Floydian Newsletter {}".format(self.initdate)
        msg['From'] = "Pink Floyd Mailer <{}>".format(self.my_email)
        msg['To'] = addressee
        self.server_connection.sendmail(self.my_email, addressee, msg.as_string())
