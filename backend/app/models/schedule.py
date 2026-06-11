from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ScheduleConfig(Base):
    __tablename__ = "schedule_config"

    id = Column(Integer, primary_key=True, default=1)
    crawl_enabled = Column(Boolean, nullable=False, default=False)
    crawl_day_of_week = Column(Integer, nullable=False, default=0)  # 0=Monday
    crawl_time = Column(String(5), nullable=False, default="06:00")  # HH:MM
    crawl_timezone = Column(String(50), nullable=False, default="Europe/Berlin")
    digest_after_crawl = Column(Boolean, nullable=False, default=True)
    digest_enabled = Column(Boolean, nullable=False, default=False)
    digest_day_of_week = Column(Integer, nullable=False, default=1)  # 1=Tuesday
    digest_time = Column(String(5), nullable=False, default="08:00")
    email_enabled = Column(Boolean, nullable=False, default=False)
    email_recipients = Column(JSON, nullable=False, default=list)
    smtp_host = Column(String(255), nullable=False, default="")
    smtp_port = Column(Integer, nullable=False, default=587)
    smtp_user = Column(String(255), nullable=False, default="")
    smtp_password = Column(String(255), nullable=False, default="")
    smtp_from = Column(String(255), nullable=False, default="")
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
