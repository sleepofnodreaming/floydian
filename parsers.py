import abc
import logging
import re
import requests
import time
import sys
from bs4 import BeautifulSoup
from collections import namedtuple

logging.basicConfig(format=u'[%(asctime)s] %(levelname)s. %(message)s', stream=sys.stderr)

News = namedtuple("News", ["source", "name", "date", "link", "text", "tagging"])


class DownloadFailedError(Exception):
    pass


class SiteParser(metaclass=abc.ABCMeta):
    """
    A base parser class.

    """

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
                parsed.append(News(self.mainpage, header, datetime, link, text, None))
        else:
            logging.critical("Wrong page format: {}".format(self.mainpage))
        return parsed


class BrainDamageParser(SiteParser):
    """
    Brain Damage main page parser.

    """

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
                text = text_pt.find_all("tr")[2].text.strip()
                parsed.append(News(self.mainpage, header, date, link, text, None))
        else:
            logging.critical("Wrong page format: {}".format(self.mainpage))
        return parsed


class PulseAndSpiritParser(SiteParser):
    """
    Pulse & Spirit main page parser.

    """

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
                tags = article.find_all("a", rel="category tag")
                tags = [tag.text for tag in tags]
                parsed.append(
                    News(self.mainpage, header, datetime_string, link, None if not text else text.text.strip(), tuple(tags))
                )
        else:
            logging.critical("Wrong page format: {}".format(self.mainpage))
        return parsed


class FloydianSlipParser(SiteParser):
    """
    Floydian Slip main page parser.

    """

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
                parsed.append(
                    News(
                        self.mainpage,
                        header,
                        time.strptime(datetime_string, self.time_format),
                        link,
                        text.strip(),
                        None
                    )
                )
        else:
            logging.critical("Wrong page format: {}".format(self.mainpage))
        return parsed

