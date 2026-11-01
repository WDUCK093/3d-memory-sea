#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把任意来源的对话导出成 memory-sea 能读的 data/my.json。

零依赖，Python 3.8+。

用法
----
    # 最少只要一份消息
    python3 export-example.py --messages chat.jsonl --out data/my.json

    # 有长期记忆和日记就一起给
    python3 export-example.py \\
        --messages chat.jsonl \\
        --longterm memory.jsonl \\
        --diaries diary.jsonl \\
        --out data/my.json

输入格式
--------
**JSONL**：每行一个 JSON 对象。

消息（每行一条）：

    {"at": 1761000000000, "sender": "me",  "text": "今天好累",     "isOwner": true}
    {"at": 1761000060000, "sender": "her", "text": "辛苦啦，先坐下", "isSelf": true}

长期记忆（每行一条）：

    {"id": "lt-1", "text": "主人对芒果过敏", "topic": "food",
     "kind": "fact", "confirmed": true, "createdAt": 1760000000000}

日记（每行一条）：

    {"date": "2026-10-27", "text": "今天他很晚才回来……", "createdAt": 1761577200000}

字段别名
--------
脚本对字段名很宽容，下面这些写法都认：

| 语义 | 认的字段名 |
|---|---|
| 时间 | `at` / `ts` / `time` / `timestamp`（毫秒；给秒会自动 ×1000） |
| 正文 | `text` / `content` / `message` / `body` |
| 说话人 | `sender` / `from` / `name` / `speaker` |
| 是她说的 | `isSelf` / `is_self` / `fromSelf` / `from_self` |
| 是对方说的 | `isOwner` / `is_owner` / `toSelf` / `to_self` |
| 日期 | `date`（`YYYY-MM-DD`）或 `at` |

⚠️ 隐私
--------
生成的 `data/my.json` 里是**真实对话**。仓库的 `.gitignore` 已经排除了
`data/my*.json` 和 `data/private*.json`，但如果你改了输出文件名，
记得自己加进 `.gitignore`。

这个脚本不联网、不上传、不读你的数据库结构——它只做格式转换。
"""

import argparse
import json
import os
import sys
import time

# ── 字段别名表 ────────────────────────────────────────────────

_TIME_KEYS = ("at", "ts", "time", "timestamp", "createdAt", "created_at")
_TEXT_KEYS = ("text", "content", "message", "body")
_SENDER_KEYS = ("sender", "from", "name", "speaker")
_SELF_KEYS = ("isSelf", "is_self", "fromSelf", "from_self")
_OWNER_KEYS = ("isOwner", "is_owner", "toSelf", "to_self")


def _pick(obj, keys, default=None):
    """按顺序找第一个存在的键。"""
    for k in keys:
        if k in obj and obj[k] is not None:
            return obj[k]
    return default


def _to_ms(value):
    """把时间统一成毫秒。小于 10^11 的当秒处理。"""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    # 2001 年之后的秒级时间戳约 1e9；毫秒约 1e12
    if n < 1e11:
        n *= 1000
    return int(n)


def _read_jsonl(path):
    """读 JSONL，跳过空行和坏行（坏行会报出第几行，但不中断）。

    用 utf-8-sig 读：Windows 记事本、PowerShell 的 Set-Content 都会给
    UTF-8 文件加 BOM，用普通 utf-8 读会让第一行解析失败。
    """
    items = []
    bad = 0
    with open(path, encoding="utf-8-sig") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                bad += 1
                print(f"  ⚠ {os.path.basename(path)} 第 {lineno} 行不是合法 JSON，已跳过（{exc.msg}）",
                      file=sys.stderr)
    if bad:
        print(f"  → {os.path.basename(path)}：{len(items)} 条可用，{bad} 条坏行", file=sys.stderr)
    return items


# ── 三种数据的归一化 ──────────────────────────────────────────


def normalize_message(raw, fallback_at):
    text = _pick(raw, _TEXT_KEYS)
    if not isinstance(text, str) or not text.strip():
        return None

    at = _to_ms(_pick(raw, _TIME_KEYS)) or fallback_at

    is_self = bool(_pick(raw, _SELF_KEYS, False))
    is_owner = bool(_pick(raw, _OWNER_KEYS, False))
    sender = _pick(raw, _SENDER_KEYS)

    # 没明确标注时，用 sender 猜一下
    if not is_self and not is_owner and isinstance(sender, str):
        low = sender.lower()
        if low in ("her", "self", "bot", "assistant", "me"):
            is_self = True
        elif low in ("owner", "user", "you", "master"):
            is_owner = True

    if not sender:
        sender = "her" if is_self else ("owner" if is_owner else "other")

    item = {
        "sender": sender,
        "text": text.strip(),
        "at": at,
    }
    if is_self:
        item["isSelf"] = True
    if is_owner:
        item["isOwner"] = True
    return item


def normalize_longterm(raw):
    text = _pick(raw, _TEXT_KEYS)
    if not isinstance(text, str) or not text.strip():
        return None

    created = _to_ms(_pick(raw, _TIME_KEYS))
    last = _to_ms(_pick(raw, ("lastMentionAt", "last_mention_at"))) or created

    item = {
        "id": raw.get("id") or f"lt-{created or int(time.time() * 1000)}",
        "text": text.strip(),
        "kind": raw.get("kind") or "fact",
        "confirmed": raw.get("confirmed", True),
        "createdAt": created or int(time.time() * 1000),
    }
    if raw.get("topic"):
        item["topic"] = raw["topic"]
    if last:
        item["lastMentionAt"] = last
    if raw.get("emotion"):
        item["emotion"] = raw["emotion"]
    return item


def normalize_diary(raw):
    text = _pick(raw, _TEXT_KEYS)
    if not isinstance(text, str) or not text.strip():
        return None

    date = raw.get("date")
    created = _to_ms(_pick(raw, _TIME_KEYS)) or int(time.time() * 1000)

    if not date:
        # 从时间戳推日期
        date = time.strftime("%Y-%m-%d", time.localtime(created / 1000))

    return {
        "date": date,
        "text": text.strip(),
        "createdAt": created,
    }


# ── 主流程 ────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(
        description="把 JSONL 对话导出成 memory-sea 的 data/my.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n  python3 export-example.py --messages chat.jsonl --out data/my.json",
    )
    ap.add_argument("--messages", required=True, help="消息 JSONL（每行一条）")
    ap.add_argument("--longterm", help="长期记忆 JSONL（可选）")
    ap.add_argument("--diaries", help="日记 JSONL（可选）")
    ap.add_argument("--out", default="data/my.json", help="输出路径（默认 data/my.json）")
    ap.add_argument("--name", default="my", help="写进 meta 的名字（默认 my）")
    args = ap.parse_args()

    print(f"读取 {args.messages} …")
    raw_msgs = _read_jsonl(args.messages)
    now = int(time.time() * 1000)

    messages = []
    for raw in raw_msgs:
        item = normalize_message(raw, now)
        if item:
            messages.append(item)

    if not messages:
        print("✗ 一条有效消息都没有，检查一下字段名（见 --help 里的别名表）", file=sys.stderr)
        return 1

    # 按时间排序，memory-sea 靠这个排时间轴
    messages.sort(key=lambda m: m["at"])

    longterm = []
    if args.longterm:
        print(f"读取 {args.longterm} …")
        for raw in _read_jsonl(args.longterm):
            item = normalize_longterm(raw)
            if item:
                longterm.append(item)

    diaries = []
    if args.diaries:
        print(f"读取 {args.diaries} …")
        for raw in _read_jsonl(args.diaries):
            item = normalize_diary(raw)
            if item:
                diaries.append(item)
    diaries.sort(key=lambda d: d["date"])

    payload = {
        "name": args.name,
        "generatedAt": now,
        "longTerm": longterm,
        "messages": messages,
        "diaries": diaries,
    }

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=None, separators=(",", ":"))

    size_kb = os.path.getsize(args.out) / 1024
    print()
    print(f"✓ 写出 {args.out}（{size_kb:.1f} KB）")
    print(f"  消息 {len(messages)} 条  长期记忆 {len(longterm)} 条  日记 {len(diaries)} 条")
    if messages:
        first = time.strftime("%Y-%m-%d %H:%M", time.localtime(messages[0]["at"] / 1000))
        last = time.strftime("%Y-%m-%d %H:%M", time.localtime(messages[-1]["at"] / 1000))
        print(f"  时间跨度 {first} → {last}")
    print()
    print("⚠ 这个文件里是真实对话，别提交到 GitHub。")
    print("  仓库的 .gitignore 已排除 data/my*.json，改过文件名的话记得自己加。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
