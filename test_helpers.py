from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session
from backend.app.api.v1._helpers import list_with_pagination

Base = declarative_base()
class MockModel(Base):
    __tablename__ = 'mock_table'
    id = Column(Integer, primary_key=True)
    name = Column(String)

engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)

session = Session(engine)
session.add_all([MockModel(name=f"item_{i}") for i in range(10)])
session.commit()

items, total = list_with_pagination(session, model=MockModel, page=1, page_size=5)
print(f"Items: {len(items)}, Total: {total}")
