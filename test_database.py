import pickle
import pytest
from database_management import *
from pony import orm

SELF_PATH = os.path.dirname(os.path.realpath(__file__))


@pytest.yield_fixture(scope="session")
def database():
    with orm.db_session:
        yield db
        db.rollback()


def newsfeeds() -> ([News], [News]):
    feeds = []
    files = ["examples/news_example_1.pickle", "examples/news_example_2.pickle"]
    examples = list(map(lambda a: os.path.join(SELF_PATH, a), files))
    for i in examples:
        with open(i, "rb") as f:
            data = pickle.load(f)
            feeds.append(data)
    return tuple(feeds)


@pytest.mark.usefixtures("database")
@pytest.mark.parametrize("fst_part,scd_part", [newsfeeds()])
def test_filling_database(fst_part: [News], scd_part: [News]):
    td = datetime.now()
    update_latest_post_urls(td, fst_part)
    current_content = orm.select(i for i in SiteSnapshot if i.timestamp == td)
    assert len(current_content) == len(fst_part)
