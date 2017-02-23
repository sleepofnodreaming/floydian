"""
The module is responsible for getting the info about the previous news letter from the database.

"""

from configuration import SELF_PATH
from datetime import datetime
from parsers import RawNews
from pony import orm

import logging
import os

DATABASE_FILE = os.path.join(SELF_PATH, 'aggregations.db')
# DATABASE_FILE = ":memory:"

db = orm.Database('sqlite', DATABASE_FILE, create_db=True)


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
def get_latest_post_urls() -> {str}:
    """
    Lists all sources' latest posts.

    :return: set of latest posts' urls.

    """
    latest_posts = (
        orm.select(p for p in SiteSnapshot)
            .prefetch(Source.name)
            .filter(
            lambda x: x.is_latest
        )
    )
    return {i.url for i in latest_posts}


@orm.db_session
def update_latest_post_urls(ts: datetime, data: [RawNews]) -> None:
    """
    Updates the data about latest posts:

    If a shop is absent from a newsfeed, nothing changes for entries related to it;
    otherwise, all the entries related to the shop are deleted, and the new set of entries' added.

    :param ts: timestamp;
    :param data: a list of News objects.
    :return: -

    """
    sources = {}
    for post in data:
        src_name, src_mp, text_link = post.parser.name, post.parser.mainpage, post.link
        if (src_name, src_mp) not in sources:
            if not Source.exists(name=src_name, newsfeed=src_mp):
                logging.info("A new source added: name = {}, newsfeed = {}".format(src_name, src_mp))
                source = Source(name=src_name, newsfeed=src_mp)
            else:
                source = Source.get(name=src_name, newsfeed=src_mp)
            sources[(src_name, src_mp)] = source
            old_latest_posts = orm.select(p for p in SiteSnapshot if p.source == source)
            if old_latest_posts:
                logging.info("Previous day's news for source '{}' found: {}.".format(src_name, len(old_latest_posts)))
                for p in old_latest_posts:
                    p.delete()
        else:
            source = sources[(src_name, src_mp)]
        logging.info("Added new post to the database: {}".format(post.link))
        SiteSnapshot(source=source, is_latest=True, timestamp=ts, url=text_link)
    logging.info("Entries in the database: {}".format(len(orm.select(p for p in SiteSnapshot))))


db.generate_mapping(create_tables=True)

if __name__ == "__main__":
    with orm.db_session:
        print(len(orm.select(p for p in SiteSnapshot)))
        for i in orm.select(p for p in SiteSnapshot):
            print(i.url, i.timestamp)
