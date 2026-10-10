from datetime import timezone
from sqlalchemy import select
from app.models import WallLike

def wall_json(row, session, visitor_hash):
    stamp = row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at
    return dict(id=str(row.id), name=row.display_name, text=row.content, emoji=row.emoji or '💬', likes=row.like_count,
                timestamp=int(stamp.timestamp()*1000), liked=bool(visitor_hash and session.scalar(select(WallLike.id).where(WallLike.message_id == row.id, WallLike.visitor_id == visitor_hash))),
                status='pending' if row.status == 'pending' else 'published', mine=bool(visitor_hash and row.visitor_hash == visitor_hash))

def project_json(p):
    return dict(slug=p.slug, title=p.title, description=p.summary, longDescription=p.description, image=p.thumbnail_url,
                category=p.category, tags=p.tech, highlights=p.highlights, video=p.video_id, demo=p.demo_url, github=p.github_url, featured=p.is_featured)
