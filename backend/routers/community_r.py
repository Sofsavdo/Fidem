"""Community features: groups, events, posts."""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from core import db, get_user, iso, now_utc, parse_dt, push_notif, user_public
from models import CreateGroupRequest, JoinGroupRequest, GroupPostRequest, new_id

router = APIRouter(tags=["community"])


# ---------- Groups ----------
@router.get("/groups")
async def list_groups(category: Optional[str] = None, region: Optional[str] = None, uid: str = Depends(get_current_user_id)):
    """List public groups, optionally filtered by category or region."""
    query = {"is_private": False}
    if category:
        query["category"] = category
    if region:
        query["region"] = region
    
    groups = await db.groups.find(query, {"_id": 0}).sort("member_count", -1).limit(50).to_list(50)
    
    # Add user's membership status
    user_groups = await db.group_members.find({"user_id": uid}).to_list(100)
    user_group_ids = {mg["group_id"] for mg in user_groups}
    
    for group in groups:
        group["is_member"] = group["id"] in user_group_ids
    
    return groups


@router.post("/groups")
async def create_group(req: CreateGroupRequest, uid: str = Depends(get_current_user_id)):
    """Create a new community group."""
    me = await get_user(uid)
    
    # Check if user can create groups (premium/vip only)
    if me.get("plan") == "free":
        raise HTTPException(402, "Group creation is premium only")
    
    group_id = new_id()
    group = {
        "id": group_id,
        "name": req.name,
        "description": req.description,
        "category": req.category,
        "region": req.region,
        "is_private": req.is_private,
        "creator_id": uid,
        "member_count": 1,
        "created_at": iso(now_utc()),
    }
    
    await db.groups.insert_one(group)
    
    # Add creator as member and admin
    await db.group_members.insert_one({
        "group_id": group_id,
        "user_id": uid,
        "role": "admin",
        "joined_at": iso(now_utc()),
    })
    
    await push_notif(uid, "community", f"Guruh yaratildi: {req.name}")
    
    return {"ok": True, "group_id": group_id}


@router.post("/groups/join")
async def join_group(req: JoinGroupRequest, uid: str = Depends(get_current_user_id)):
    """Join a public group."""
    group = await db.groups.find_one({"id": req.group_id})
    if not group:
        raise HTTPException(404, "Group not found")
    
    if group["is_private"]:
        raise HTTPException(403, "Cannot join private group directly")
    
    # Check if already a member
    existing = await db.group_members.find_one({"group_id": req.group_id, "user_id": uid})
    if existing:
        raise HTTPException(400, "Already a member")
    
    await db.group_members.insert_one({
        "group_id": req.group_id,
        "user_id": uid,
        "role": "member",
        "joined_at": iso(now_utc()),
    })
    
    await db.groups.update_one({"id": req.group_id}, {"$inc": {"member_count": 1}})
    
    await push_notif(uid, "community", f"{group['name']} guruhiga qo'shildingiz")
    
    return {"ok": True}


@router.post("/groups/leave")
async def leave_group(req: JoinGroupRequest, uid: str = Depends(get_current_user_id)):
    """Leave a group."""
    membership = await db.group_members.find_one({"group_id": req.group_id, "user_id": uid})
    if not membership:
        raise HTTPException(404, "Not a member")
    
    # Admins cannot leave their own groups
    if membership["role"] == "admin":
        raise HTTPException(403, "Admins cannot leave their own groups")
    
    await db.group_members.delete_one({"group_id": req.group_id, "user_id": uid})
    await db.groups.update_one({"id": req.group_id}, {"$inc": {"member_count": -1}})
    
    return {"ok": True}


@router.get("/groups/{group_id}/posts")
async def group_posts(group_id: str, uid: str = Depends(get_current_user_id)):
    """Get posts from a group."""
    # Check if user is a member
    membership = await db.group_members.find_one({"group_id": group_id, "user_id": uid})
    if not membership:
        raise HTTPException(403, "Not a member of this group")
    
    posts = await db.group_posts.find({"group_id": group_id}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    
    # Enrich with user info
    for post in posts:
        user = await get_user(post["user_id"])
        post["user"] = user_public(user) if user else None
    
    return posts


@router.post("/groups/posts")
async def create_post(req: GroupPostRequest, uid: str = Depends(get_current_user_id)):
    """Create a post in a group."""
    # Check if user is a member
    membership = await db.group_members.find_one({"group_id": req.group_id, "user_id": uid})
    if not membership:
        raise HTTPException(403, "Not a member of this group")
    
    post = {
        "id": new_id(),
        "group_id": req.group_id,
        "user_id": uid,
        "text": req.text,
        "created_at": iso(now_utc()),
        "likes": 0,
        "comments": 0,
    }
    
    await db.group_posts.insert_one(post)
    await db.groups.update_one({"id": req.group_id}, {"$inc": {"post_count": 1}})
    
    # Notify group members (simplified - in production would be batched)
    return {"ok": True, "post_id": post["id"]}


@router.post("/groups/posts/{post_id}/like")
async def like_post(post_id: str, uid: str = Depends(get_current_user_id)):
    """Like a group post."""
    post = await db.group_posts.find_one({"id": post_id})
    if not post:
        raise HTTPException(404, "Post not found")
    
    # Check if already liked
    existing = await db.group_post_likes.find_one({"post_id": post_id, "user_id": uid})
    if existing:
        # Toggle: remove like
        await db.group_post_likes.delete_one({"post_id": post_id, "user_id": uid})
        await db.group_posts.update_one({"id": post_id}, {"$inc": {"likes": -1}})
        return {"ok": True, "liked": False}
    else:
        # Add like
        await db.group_post_likes.insert_one({
            "post_id": post_id,
            "user_id": uid,
            "created_at": iso(now_utc()),
        })
        await db.group_posts.update_one({"id": post_id}, {"$inc": {"likes": 1}})
        return {"ok": True, "liked": True}


# ---------- Events ----------
@router.get("/events")
async def list_events(region: Optional[str] = None, uid: str = Depends(get_current_user_id)):
    """List upcoming events."""
    query = {"event_date": {"$gte": iso(now_utc())}}
    if region:
        query["region"] = region
    
    events = await db.events.find(query, {"_id": 0}).sort("event_date", 1).limit(20).to_list(20)
    
    # Add user's RSVP status
    user_rsvps = await db.event_rsvps.find({"user_id": uid}).to_list(100)
    user_event_ids = {rsvp["event_id"] for rsvp in user_rsvps}
    
    for event in events:
        event["is_rsvped"] = event["id"] in user_event_ids
    
    return events


@router.post("/events/{event_id}/rsvp")
async def rsvp_event(event_id: str, uid: str = Depends(get_current_user_id)):
    """RSVP to an event."""
    event = await db.events.find_one({"id": event_id})
    if not event:
        raise HTTPException(404, "Event not found")
    
    # Check if already RSVPed
    existing = await db.event_rsvps.find_one({"event_id": event_id, "user_id": uid})
    if existing:
        # Toggle: remove RSVP
        await db.event_rsvps.delete_one({"event_id": event_id, "user_id": uid})
        await db.events.update_one({"id": event_id}, {"$inc": {"rsvp_count": -1}})
        return {"ok": True, "rsvped": False}
    else:
        # Add RSVP
        await db.event_rsvps.insert_one({
            "event_id": event_id,
            "user_id": uid,
            "created_at": iso(now_utc()),
        })
        await db.events.update_one({"id": event_id}, {"$inc": {"rsvp_count": 1}})
        await push_notif(uid, "community", f"Eventga ro'yxatdan o'tdingiz: {event['title']}")
        return {"ok": True, "rsvped": True}
