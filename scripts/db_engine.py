from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy import and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

DATABASE_URL = "sqlite:///brainrot.db"
Base = declarative_base()

class VideoQueue(Base):
    __tablename__ = "video_queue"
    id = Column(Integer, primary_key=True, index=True)
    
    # Metadata
    original_filename = Column(String)
    streamer_name = Column(String)
    file_path = Column(String) # Path to the EDITED video
    
    # Scheduling
    status = Column(String, default="PENDING") # PENDING, UPLOADED, FAILED
    scheduled_time = Column(DateTime, nullable=True)
    uploaded_at = Column(DateTime, nullable=True)
    
    # Learning
    youtube_id = Column(String, nullable=True)
    views = Column(Integer, default=0)
    hashtag_set = Column(String, default="default") # Track which tags were used

class CreatorHistory(Base):
    __tablename__ = "creator_history"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, index=True)
    creator_id = Column(String, index=True)
    creator_name = Column(String)
    last_used_at = Column(DateTime, nullable=True)

class ClipHistory(Base):
    __tablename__ = "clip_history"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, index=True)
    clip_id = Column(String, index=True)
    clip_url = Column(String)
    creator_id = Column(String)
    used_at = Column(DateTime, nullable=True)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def add_video_to_queue(path, streamer):
    db = SessionLocal()
    new_vid = VideoQueue(file_path=path, streamer_name=streamer, status="PENDING")
    db.add(new_vid)
    db.commit()
    db.close()
    print(f"[DB] Queued video for {streamer}")

def get_next_video():
    db = SessionLocal()
    # FIFO: First In, First Out
    video = db.query(VideoQueue).filter(VideoQueue.status == "PENDING").first()
    db.close()
    return video

def mark_uploaded(video_id, yt_id, used_tags):
    db = SessionLocal()
    vid = db.query(VideoQueue).filter(VideoQueue.id == video_id).first()
    vid.status = "UPLOADED"
    vid.uploaded_at = datetime.now()
    vid.youtube_id = yt_id
    vid.hashtag_set = used_tags
    db.commit()
    db.close()

def mark_failed(video_id):
    db = SessionLocal()
    vid = db.query(VideoQueue).filter(VideoQueue.id == video_id).first()
    if vid:
        vid.status = "FAILED"
        db.commit()
    db.close()

def is_creator_recently_used(platform, creator_id, within_days=7):
    db = SessionLocal()
    cutoff = datetime.now() - timedelta(days=within_days)
    row = db.query(CreatorHistory).filter(
        and_(
            CreatorHistory.platform == platform,
            CreatorHistory.creator_id == creator_id,
            CreatorHistory.last_used_at != None,
            CreatorHistory.last_used_at >= cutoff
        )
    ).first()
    db.close()
    return row is not None

def mark_creator_used(platform, creator_id, creator_name):
    db = SessionLocal()
    row = db.query(CreatorHistory).filter(
        and_(
            CreatorHistory.platform == platform,
            CreatorHistory.creator_id == creator_id
        )
    ).first()
    if not row:
        row = CreatorHistory(platform=platform, creator_id=creator_id, creator_name=creator_name)
        db.add(row)
    row.last_used_at = datetime.now()
    db.commit()
    db.close()

def is_clip_used(platform, clip_id):
    db = SessionLocal()
    row = db.query(ClipHistory).filter(
        and_(
            ClipHistory.platform == platform,
            ClipHistory.clip_id == clip_id
        )
    ).first()
    db.close()
    return row is not None

def mark_clip_used(platform, clip_id, clip_url, creator_id):
    db = SessionLocal()
    row = ClipHistory(
        platform=platform,
        clip_id=clip_id,
        clip_url=clip_url,
        creator_id=creator_id,
        used_at=datetime.now()
    )
    db.add(row)
    db.commit()
    db.close()
