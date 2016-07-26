import pickle
import pytest
from database_management import *
from pony import orm

SELF_PATH = os.path.dirname(os.path.realpath(__file__))


@pytest.yield_fixture(scope="function")
def database():
    with orm.db_session:
        yield db
        db.rollback()

@pytest.fixture(scope="session")
def newsfeeds() -> [([News, News])]:
    with open(os.path.join(SELF_PATH, "examples/newsfeeds.pickle"), "rb") as f:
        data = pickle.load(f)
        return data


# todo convert this to many tests arranged chronologically.
@pytest.mark.usefixtures("database", "newsfeeds")
def test_filling_database(newsfeeds):
    """
    The test checks whether the replacement of news page stamps is executed correctly.

    """
    # Making the news set empty.
    fst_set, scd_set = newsfeeds
    orm.delete(i for i in SiteSnapshot)
    assert len(orm.select(i for i in SiteSnapshot)) == 0
    # Then, trying to add four news from the first set.
    td = datetime.now()
    fst_pt, scd_pt = fst_set
    # Here, a data set of 26 news from four sources are added to the db.
    update_latest_post_urls(td, scd_pt)
    assert len(orm.select(i for i in SiteSnapshot)) == 26
    # Here, however, the
    update_latest_post_urls(td, fst_pt)
    assert len(orm.select(i for i in SiteSnapshot)) == 4
    fst_pt, scd_pt = scd_set
    update_latest_post_urls(td, fst_pt)
    assert len(orm.select(i for i in SiteSnapshot)) == len(fst_pt) + 2
    update_latest_post_urls(td, scd_pt)
    assert len(orm.select(i for i in SiteSnapshot)) == len(fst_pt) + len(scd_pt)

