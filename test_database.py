import pickle
import pytest
from database_management import *
from pony import orm

SELF_PATH = os.path.dirname(os.path.realpath(__file__))


@pytest.yield_fixture(scope="session")
def database():
    with orm.db_session:
        orm.delete(i for i in SiteSnapshot)
        yield db
        db.rollback()


def newsfeeds():
    with open(os.path.join(SELF_PATH, "examples/newsfeeds.pickle"), "rb") as f:
        data = pickle.load(f)
        ((full_overlap_two, full_overlap_one), (exclusive_one, exclusive_two)) = data
        return [
            (full_overlap_one, 0, 26),
            (full_overlap_two, 26, 4),
            (exclusive_one, 4, len(exclusive_one) + 2),
            (exclusive_two, len(exclusive_one) + 2, len(exclusive_one) + len(exclusive_two)),
        ]


@pytest.mark.usefixtures("database")
@pytest.mark.parametrize("feed,b,a", newsfeeds())
def test_filling_database(feed, b, a):
    """
    The test checks whether the replacement of news page stamps is executed correctly.

    """
    # If a test failed here, parametrized tests' order may have become random :(
    assert len(orm.select(i for i in SiteSnapshot)) == b
    # Then, trying to add four news from the first set.
    td = datetime.now()
    update_latest_post_urls(td, feed)
    assert len(orm.select(i for i in SiteSnapshot)) == a
