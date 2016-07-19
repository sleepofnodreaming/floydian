from collections import namedtuple
from datetime import datetime
from pony import orm

import logging
import os
import sys

logging.basicConfig(format=u'[%(asctime)s] %(levelname)s. %(message)s', stream=sys.stderr, level=logging.INFO)
# DATABASE_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'aggregations.db')
DATABASE_FILE = ":memory:"

db = orm.Database('sqlite', DATABASE_FILE, create_db=True)


NewsStamp = namedtuple("NewsStamp", ["parser_name", "parser_newsfeed", "news_url", "news_extraction_time"])


class Source(db.Entity):
    """
    A model corresponding to sites used as data sources.

    """
    name = orm.Required(str, 255, unique=True)
    newsfeed = orm.Required(str, 1000, unique=True)
    snapshot = orm.Set("SiteSnapshot")


class SiteSnapshot(db.Entity):
    """
    A model of last posts in a site's news feed.

    """
    url = orm.Required(str)
    timestamp = orm.Required(datetime)
    source = orm.Required("Source", reverse="snapshot")
    is_latest = orm.Required(bool)


@orm.db_session
def get_latest_post_urls() -> {str: str}:
    """
    List all sources' latest posts.

    :param parser_names: names of sources we are interested in& If empty, all names are included;
    :return: {source name (str): latest post url (str)}.

    """
    latest_posts = (
        orm.select(p for p in SiteSnapshot)
            .prefetch(Source.name)
            .filter(
            lambda x: x.is_latest
        )
    )
    return {i.source.name: i.url for i in latest_posts}


@orm.db_session
def update_latest_post_urls(data: [NewsStamp]) -> None:
    """
    Update the data about latest posts.

    :param data: a list of NewsStamp objects.
    :return: None.

    """
    for post_tup in data:
        if not Source.exists(name=post_tup.parser_name, newsfeed=post_tup.parser_newsfeed):
            logging.info("A new source added: name = {}, newsfeed = {}".format(
                post_tup.parser_name,
                post_tup.parser_newsfeed
            ))
            source = Source(name=post_tup.parser_name, newsfeed=post_tup.parser_newsfeed)
        else:
            source = Source.get(name=post_tup.parser_name, newsfeed=post_tup.parser_newsfeed)
            old_latest_post = SiteSnapshot.get(source=source)
            if old_latest_post:
                old_latest_post.delete()
        SiteSnapshot(source=source, is_latest=True, timestamp=post_tup.news_extraction_time, url=post_tup.news_url)


if __name__ == '__main__':
    db.generate_mapping(create_tables=True)
    print(get_latest_post_urls())

