from app.db.base import Base
from app.db.session import engine


def init_db() -> None:
    # 각 담당자는 새 모델을 app.models에서 import되도록 등록해야 합니다.
    import app.models  # noqa: F401, PLC0415

    Base.metadata.create_all(bind=engine)

