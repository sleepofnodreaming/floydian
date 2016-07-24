import abc
import logging
import re
import requests
import time
from bs4 import BeautifulSoup
from collections import namedtuple


News = namedtuple("News", ["parser", "name", "date", "link", "text", "tagging"])


class DownloadFailedError(Exception):
    pass


def to_paragraphs(text: str) -> [str]:
    """
    The functions splits a text into paragraphs.

    :param text: a text of a post, where paragraphs are separated with '\n's.
    :return: a list of paragraphs.

    """
    if not text:
        return []
    ps = [i.strip() for i in text.split("\n")]
    return [p for p in ps if p]


class SiteParser(metaclass=abc.ABCMeta):
    """
    A base parser class.

    """
    name = ""
    lang = "en"

    def __init__(self, mainpage):
        """
        The method initializes a parser instance.

        :param mainpage: a URL of a web page containing the latest news.
        :return: None.

        """
        self.mainpage = mainpage
        self.html = None

    def download_page(self):
        """
        The method re-downloads the news page and assigns it to a self.html attribute.

        :return: None.

        """
        resp = requests.get(self.mainpage)
        if resp.status_code != 200 or not resp.headers['content-type'].startswith("text/html"):
            raise DownloadFailedError()
        self.html = resp.text

    @abc.abstractmethod
    def to_news(self):
        """
        The method parses a html saved to the self.html attribute.
        WARNING: Override this method subclassing the parser.

        :return: a list of News instances.

        """
        return []

    @property
    def news(self):
        """
        Getter for a list of news.

        :return: a list of News instances.

        """
        try:
            self.download_page()
        except DownloadFailedError:
            logging.critical("Error downloading page: {}".format(self.mainpage))
            return []
        if not self.html:
            logging.critical("Page is empty: {}".format(self.mainpage))
            return []
        return self.to_news()


class AFGParser(SiteParser):
    """
    A Fleeting Glimpse parser.

    """

    name = "A Fleeting Glimpse"

    def __init__(self):
        SiteParser.__init__(self, "http://www.pinkfloydz.com/")

    def to_news(self):
        soup = BeautifulSoup(self.html, "lxml")
        parsed = []
        article_parent = soup.find("div", class_="wvrx-posts")
        if article_parent:
            articles = article_parent.find_all("article")
            for article in articles:
                dt = article.find("time")
                datetime = None if not dt else time.strptime(dt["datetime"], "%Y-%m-%dT%H:%M:%S+00:00")
                header_link = article.find("a", rel="bookmark")
                header = None if not header_link else header_link.text
                link = None if not header_link else header_link["href"]
                if not header or not link:
                    continue
                text = article.find("div", class_=re.compile("entry-(content|summary)"))
                if text:
                    text = text.text.strip()
                    continue_template = "Continue reading →"
                    if text.endswith(continue_template):
                        text = text[:-len(continue_template)]
                txt = to_paragraphs(text)
                parsed.append(News(self, header, datetime, link, txt, []))
        else:
            logging.critical("Wrong page format: {}".format(self.mainpage))
        return parsed


class BrainDamageParser(SiteParser):
    """
    Brain Damage main page parser.

    """

    name = "Brain Damage"

    def __init__(self):
        SiteParser.__init__(self, "http://www.brain-damage.co.uk/index.php")

    def to_news(self):
        soup = BeautifulSoup(self.html, "lxml")
        parsed = []
        article_parent = soup.find("table", class_="blog")
        if article_parent:
            articles = article_parent.find_all("table", class_="contentpaneopen")
            # Even cells are texts, odd cells are headlines.
            for header_pt, text_pt in zip(articles[::2], articles[1::2]):
                header_link = header_pt.find("a", class_="contentpagetitle")
                header = None if not header_link else header_link.text.strip()
                link = None if not header_link else header_link["href"]
                if not header or not link:
                    continue
                date = text_pt.find("td", class_="createdate")
                date = None if not date else date.text.strip()
                date = None if not date else time.strptime(date, "%A, %d %B %Y")
                text = text_pt.find_all("tr")
                paragraphs = [] if not len(text) > 2 else to_paragraphs(text[2].text.strip())
                parsed.append(News(self, header, date, link, paragraphs, []))
        else:
            logging.critical("Wrong page format: {}".format(self.mainpage))
        return parsed


class PulseAndSpiritParser(SiteParser):
    """
    Pulse & Spirit main page parser.

    """

    name = "Pulse & Spirit"
    lang = "de"

    def __init__(self):
        SiteParser.__init__(self, "http://www.pulse-and-spirit.com/")

    def to_news(self):
        soup = BeautifulSoup(self.html, "lxml")
        parsed = []
        article_parent = soup.find("section", class_="content")
        if article_parent:
            articles = article_parent.find_all("article")
            for article in articles:
                dt = article.find("time")
                datetime_string = None if not dt else time.strptime(dt["datetime"], "%Y-%m-%d %H:%M:%S")
                header_link = article.find("a", rel="bookmark")
                header = None if not header_link else header_link.text
                link = None if not header_link else header_link["href"]
                if not header or not link:
                    continue
                text = article.find("div", class_="entry-summary")
                ptext = [] if not text else to_paragraphs(text.text.strip())
                tags = article.find_all("a", rel="category tag")
                tags = [tag.text for tag in tags]
                parsed.append(
                    News(
                        self,
                        header,
                        datetime_string,
                        link,
                        ptext,
                        tags,
                    )
                )
        else:
            logging.critical("Wrong page format: {}".format(self.mainpage))
        return parsed


class FloydianSlipParser(SiteParser):
    """
    Floydian Slip main page parser.

    """

    name = "Floydian Slip"

    def __init__(self):
        SiteParser.__init__(self, "http://www.floydianslip.com/news/")
        self._date_parser = re.compile(r"^Posted (.*?) by", flags=re.U)
        self.time_format = "%B %d, %Y"

    def to_news(self):
        soup = BeautifulSoup(self.html, "lxml")
        parsed = []
        article_parent = soup.find("div", class_="row contentArea last")
        if article_parent:
            articles = article_parent.find_all("div", id=re.compile('post-\d+'))
            for article in articles:
                dt = article.find("p", class_="blogSlug")
                datetime_string = None if not dt else dt.text.strip()
                if not datetime_string:
                    continue
                datetime_string = self._date_parser.search(datetime_string)
                if not datetime_string:
                    continue
                datetime_string = datetime_string.group(1)

                header_link = article.find("a", rel="bookmark")
                header = None if not header_link else header_link.text
                link = None if not header_link else header_link["href"]
                if not header or not link:
                    continue
                text = article.find("div", class_="entry").text
                ptext = to_paragraphs(None if not text else text.strip())
                parsed.append(
                    News(
                        self,
                        header,
                        time.strptime(datetime_string, self.time_format),
                        link,
                        ptext,
                        [],
                    )
                )
        else:
            logging.critical("Wrong page format: {}".format(self.mainpage))
        return parsed
